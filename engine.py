"""Directional OpenAPI 3 schema compatibility and consumer impact analysis.
Only local #/components/schemas references are resolved. Unsupported composition
is reported as unknown instead of being treated as compatible.
"""
from collections import deque
from copy import deepcopy
import hashlib,json

def analyze(data):
    before,after=data['before'],data['after']
    for spec in (before,after):
        if not str(spec.get('openapi','')).startswith('3.'):
            raise ValueError('Both documents must be OpenAPI 3.x JSON objects')
    changes=[]
    def emit(code,path,detail,severity='breaking'):
        changes.append(dict(code=code,path=path,detail=detail,severity=severity))
    def deref(s,spec,seen=()):
        if not isinstance(s,dict):raise ValueError('Schema must be an object')
        ref=s.get('$ref')
        if not ref:return s
        if not ref.startswith('#/components/schemas/'):
            raise ValueError('External references are unsupported: '+ref)
        if ref in seen:return {'__recursive__':ref}
        cur=spec
        for part in ref[2:].split('/'):
            key=part.replace('~1','/').replace('~0','~')
            if not isinstance(cur,dict) or key not in cur:raise ValueError('Unresolved reference: '+ref)
            cur=cur[key]
        return deref(cur,spec,seen+(ref,))
    def compare(a,b,path,direction,depth=0,seen=frozenset()):
        if depth>40:
            emit('analysis_limit',path,'Schema nesting exceeded 40 levels','unknown');return
        a,b=deref(a,before),deref(b,after)
        identity=(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True),direction)
        if identity in seen:
            emit('recursive_schema',path,'Recursive schema pair requires manual review','unknown');return
        seen=seen|{identity}
        if '__recursive__' in a or '__recursive__' in b:
            emit('recursive_schema',path,'Recursive reference requires manual review','unknown');return
        unsupported=['allOf','oneOf','anyOf','not','if','then','else','unevaluatedProperties','patternProperties','$dynamicRef']
        if any(k in a or k in b for k in unsupported):
            emit('composition_review',path,'Composition or conditional schema requires manual review','unknown')
        # Requests must accept existing inputs. Responses must remain acceptable to old consumers.
        old_types=set(a.get('type',[]) if isinstance(a.get('type'),list) else [a.get('type')])-{None}
        new_types=set(b.get('type',[]) if isinstance(b.get('type'),list) else [b.get('type')])-{None}
        if a.get('nullable'):old_types.add('null')
        if b.get('nullable'):new_types.add('null')
        safe=(old_types<=new_types if direction=='request' else new_types<=old_types)
        if old_types and new_types and not safe:
            emit('type_changed',path,f'Types changed from {sorted(old_types)} to {sorted(new_types)} ({direction})')
        elif old_types!=new_types and (old_types or new_types):
            emit('type_constraint_changed',path,'Type constraint added or removed; review compatibility','unknown')
        old_enum,new_enum=a.get('enum'),b.get('enum')
        if old_enum is not None or new_enum is not None:
            aa=set(map(lambda x:json.dumps(x,sort_keys=True),old_enum or []));bb=set(map(lambda x:json.dumps(x,sort_keys=True),new_enum or []))
            incompatible=(new_enum is not None and (old_enum is None or not aa<=bb)) if direction=='request' else (old_enum is not None and (new_enum is None or not bb<=aa))
            if incompatible:emit('enum_incompatible',path,f'Allowed values changed for {direction}')
        ap,bp=a.get('properties',{}),b.get('properties',{})
        ar,br=set(a.get('required',[])),set(b.get('required',[]))
        for key in sorted(br-ar if direction=='request' else ar-br):
            emit('required_incompatible',path+'/'+key,'New required request field' if direction=='request' else 'Response field is no longer guaranteed')
        if direction=='response':
            for key in sorted(set(ap)-set(bp)):emit('response_field_removed',path+'/'+key,'Previously documented response field removed')
        if direction=='request' and b.get('additionalProperties') is False:
            for key in sorted(set(ap)-set(bp)):emit('request_field_rejected',path+'/'+key,'Existing request field is now forbidden')
            if a.get('additionalProperties') is not False:
                emit('additional_properties_restricted',path,'Additional request fields are now forbidden')
        if direction=='response' and a.get('additionalProperties') is False:
            if set(bp)-set(ap) or b.get('additionalProperties') is not False:
                emit('response_properties_expanded',path,'Old closed response schema may reject new properties')
        for key in sorted(set(ap)&set(bp)):compare(ap[key],bp[key],path+'/'+key,direction,depth+1,seen)
        if isinstance(a.get('items'),dict) and isinstance(b.get('items'),dict):compare(a['items'],b['items'],path+'/*',direction,depth+1,seen)
        for key,lower in [('minimum',True),('minLength',True),('minItems',True),('maximum',False),('maxLength',False),('maxItems',False)]:
            av,bv=a.get(key),b.get(key)
            if av==bv:continue
            if direction=='request':incompatible=bv is not None and (av is None or (bv>av if lower else bv<av))
            else:incompatible=av is not None and (bv is None or (bv<av if lower else bv>av))
            if incompatible:emit('bound_incompatible',path,f'{key}: {av!r} → {bv!r} ({direction})')
        for key in ['format','pattern','exclusiveMinimum','exclusiveMaximum','uniqueItems']:
            if a.get(key)!=b.get(key):emit('constraint_review',path,f'{key} changed; manual compatibility review','unknown')
    methods={'get','put','post','delete','options','head','patch','trace'}
    def operations(spec):
        return {f'{m.upper()} {p}':(item,op) for p,item in spec.get('paths',{}).items() for m,op in item.items() if m in methods}
    old,new=operations(before),operations(after)
    for operation,(old_path,a) in sorted(old.items()):
        if operation not in new:
            emit('operation_removed',operation,'Existing API operation removed');continue
        new_path,b=new[operation]
        if any('$ref' in p for p in old_path.get('parameters',[])+a.get('parameters',[])+new_path.get('parameters',[])+b.get('parameters',[])):
            emit('parameter_reference_review',operation,'Referenced parameters require manual review','unknown')
        old_params={(p['in'],p['name']):p for p in old_path.get('parameters',[])+a.get('parameters',[]) if '$ref' not in p}
        new_params={(p['in'],p['name']):p for p in new_path.get('parameters',[])+b.get('parameters',[]) if '$ref' not in p}
        for key,p in new_params.items():
            if p.get('required') and (key not in old_params or not old_params[key].get('required')):emit('parameter_required',operation+f'/parameters/{key[0]}/{key[1]}','Parameter newly required')
            if key in old_params:compare(old_params[key].get('schema',{}),p.get('schema',{}),operation+f'/parameters/{key[0]}/{key[1]}','request')
        ra,rb=a.get('requestBody',{}),b.get('requestBody',{})
        if '$ref' in ra or '$ref' in rb:emit('body_reference_review',operation,'Referenced request bodies require manual review','unknown')
        if rb.get('required') and not ra.get('required'):emit('body_required',operation,'Request body newly required')
        for media,content in ra.get('content',{}).items():
            if media not in rb.get('content',{}):emit('request_media_removed',operation+'/request/'+media,'Request media type removed')
            else:compare(content.get('schema',{}),rb['content'][media].get('schema',{}),operation+'/request/'+media,'request')
        for status,res in a.get('responses',{}).items():
            if status not in b.get('responses',{}):emit('response_status_removed',operation+'/response/'+status,'Documented response status removed');continue
            if '$ref' in res or '$ref' in b['responses'][status]:emit('response_reference_review',operation+'/response/'+status,'Referenced responses require manual review','unknown')
            for media,content in res.get('content',{}).items():
                target=b['responses'][status].get('content',{})
                if media not in target:emit('response_media_removed',operation+'/response/'+status+'/'+media,'Response media type removed')
                else:compare(content.get('schema',{}),target[media].get('schema',{}),operation+'/response/'+status+'/'+media,'response')
        old_security=a.get('security',before.get('security',[]));new_security=b.get('security',after.get('security',[]))
        if old_security!=new_security:emit('security_changed',operation,'Security requirements changed; verify clients','unknown')
    consumers=data.get('consumers',[]);ids=[x['id'] for x in consumers]
    if len(ids)!=len(set(ids)):raise ValueError('Consumer IDs must be unique')
    known=set(ids);reverse={i:[] for i in ids};operations_by_consumer={x['id']:set(x.get('operations',[])) for x in consumers}
    for c in consumers:
        for dependency in c.get('dependsOn',[]):
            if dependency not in known:raise ValueError('Unknown consumer dependency: '+dependency)
            reverse[dependency].append(c['id'])
    changed_ops={op for op in old if any(c['path']==op or c['path'].startswith(op+'/') for c in changes)}
    queue=deque((cid,[cid]) for cid,ops in operations_by_consumer.items() if ops&changed_ops);impact={}
    while queue:
        cid,chain=queue.popleft()
        if cid in impact:continue
        impact[cid]={'consumer':cid,'chain':chain,'direct':len(chain)==1}
        for dependent in sorted(reverse[cid]):queue.append((dependent,chain+[dependent]))
    fingerprint=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'product':'ContractGraph','version':'0.1.0','summary':{'breaking':sum(c['severity']=='breaking' for c in changes),'manualReview':sum(c['severity']=='unknown' for c in changes),'impactedConsumers':len(impact),'operationsCompared':len(old)},'findings':changes,'impact':list(impact.values()),'provenance':{'inputSha256':fingerprint},'limitations':['Conservative schema checks, not a complete OpenAPI compatibility proof.','Only local schema references; composition, recursion and some constraints require manual review.','Consumer impact follows declared dependencies, not observed runtime traffic.']}
