#! /usr/bin/bash
set -e
set -o xtrace


script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
host_package_dir=$(dirname "$script_dir")
container_package_dir=/usr/local/src/nbs-gui

version="0.0.1"

container=$(buildah from nbs)
buildah run $container -- dnf -y install qt5-qtbase-devel
buildah run $container -- conda install -y pyqt
buildah run $container -- pip3 install bluesky_queueserver_api qtconsole

buildah copy $container $host_package_dir $container_package_dir 
buildah run --workingdir $container_package_dir $container -- pip3 install .

buildah config --cmd "nbs-gui --profile default" $container

buildah unmount $container

buildah commit $container nbs_gui:$version
buildah commit $container nbs_gui:latest

buildah rm $container
