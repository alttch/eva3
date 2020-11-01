VERSION=3.3.2

all:
	@echo "Branch: `git branch|grep ^*`"
	@echo
	@echo -n "Current build:"
	@grep "^product_build = " sbin/ucserv.py|cut -d= -f2|awk '{ print $1 }'
	@./sbin/uc-control version
	@./sbin/lm-control version
	@./sbin/sfa-control version

pub:
	git push
	jks build eva-${VERSION}

test-build:
	make build
	git commit -a -m 'test build'
	git push
	jks build get.eva-ics.com
	make test-release

d:
	mkdir -p dist
	@./dev/make-dist

dmaster:
	mkdir -p dist
	@./dev/make-dist master

release:
	@./dev/make-release
	jks build get.eva-ics.com

test-release:
	@./dev/make-release --test

test:
	lab-xs4 on
	ssh -t lab-xs4 "cd /opt/et && make test-c"

test-full:
	lab-xs4 on
	ssh -t lab-xs4 "cd /opt/et && make test"

t:
	cd doc && make clean html

ch:
	@./dev/upload-changelog

build: build-increase

build-increase:
	sh ./dev/increase_build_version

check:
	@./dev/check_code

start:
	./sbin/eva-control start

stop:
	./sbin/eva-control stop

restart:
	./sbin/eva-control restart

ver: build-increase update-version

update-version:
	find bin -name "*" -type f -exec sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/g" {} \;
	find cli -name "*" -type f -exec sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/g" {} \;
	find sbin -name "*" -type f -exec sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/g" {} \;
	find lib -name "*.py" -type f -exec sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/g" {} \;
	find doc -name "*.py" -type f -exec sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/g" {} \;
	find xc/drivers/tools -name "*.py" -type f -exec sed -i "s/^__version__ = .*/__version__ = \"${VERSION}\"/g" {} \;
	find . -name "*.js" ! -name "chart.min.js" -exec sed -i "s/* Version: .*/* Version: ${VERSION}/g" {} \;
	find . -name "*.php" -exec sed -i "s/eva_version = .*/eva_version = '${VERSION}';/g" {} \;
	find . -name "*.php" -exec sed -i "s/@version .*/@version     ${VERSION}/g" {} \;
	find . -name "*" ! -name "Makefile" -type f -exec sed -i "s/\((C) 2012-\)[0-9]*/\1`date "+%Y"`/g" {} \;
	sed -i "s/^VERSION=.*/VERSION=${VERSION}/g" update.sh
	#sed -i "s/^eva_sfa_framework_version =.*/eva_sfa_framework_version = \"${VERSION}\";/g" ui/js/eva_sfa.js

yapf:
	find . -name "*.py" -exec yapf --style google -i {} \;

min:
	./dev/make-min

#pub-compose:
	#scp -P 222 install/demos/eva_basic/docker-compose.yml root@d1.altertech.net:/www/download/eva-ics/configs/
	#gsutil cp -a public-read install/demos/eva_basic/docker-compose.yml gs://get.eva-ics.com/configs/
	#cd /opt/eva-ics.com/indexer && make prefix=/configs pub

#demo-basic:
	#./dev/make-demo basic

#demo-farm:
	#./dev/make-demo farm

clean:
	docker-compose down

man:
	cd doc && make html

completion:
	./dev/gen-complete.sh

env:
	./install/build-venv
	#./python3/bin/pip install ipython ipdb
