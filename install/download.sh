#!/bin/sh

[ ${repo_uri} ] || repo_uri=https://get.eva-ics.com

[ ! ${force_version} ] && VERSION=`curl -s ${repo_uri}/update_info.json|jq -r .version` || VERSION=${force_version}
[ ! ${force_build} ] && BUILD=`curl -s ${repo_uri}/update_info.json|jq -r .build` || BUILD=${force_build}
[ ! ${force_nightly} ] && DT=stable || DT=nightly

if [ "x${BUILD}" = "x" ] || [ "x${VERSION}" = "x" ]; then
    exit 5
fi

[ ! ${force_distro} ] && DIST=${repo_uri}/${VERSION}/${DT}/eva-${VERSION}-${BUILD}.tgz || DIST=${force_distro}

rm -f eva-dist.tgz
curl ${DIST} -o eva-dist.tgz || exit 1
exit 0
