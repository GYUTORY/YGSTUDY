import os, sys
os.chdir('/root/YGSTUDY')
sys.argv = ['gen_nav.py']
exec(open('tools/gen_nav.py').read())
gen = walk_and_generate()
hub_key = 'Develop/_hub'
for k, v in gen.items():
    if k == hub_key:
        print('=== 생성될 Develop/_hub/.pages ===')
        print(v)
        break
