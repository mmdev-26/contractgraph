import resource,sys
resource.setrlimit(resource.RLIMIT_CPU,(3,3))
if sys.platform.startswith('linux'):resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
sys.argv=[sys.argv[0],'analyze','-']
from app import main
main()
