from pybuilder.core import init, use_plugin, task

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.coverage")
use_plugin("python.install_dependencies")

default_task = "publish"


@init
def initialize(project):
    project.build_depends_on("coverage==4.2")
    project.build_depends_on("future==0.15.2")
    project.build_depends_on("mock==2.0.0")
    project.build_depends_on("nose==1.3.7")
    project.build_depends_on("pbr==1.10.0")
    project.build_depends_on("pefile==2016.3.28")
    project.build_depends_on("PyInstaller==3.2")
    # project.build_depends_on('pypiwin32==219')
    project.build_depends_on("python-redmine==1.5.1")
    project.build_depends_on("PyYAML==3.11")
    project.build_depends_on("requests==2.11.0")
    project.build_depends_on("six==1.10.0")
    project.build_depends_on("jira==2.0.0")
    project.build_depends_on("python-dateutil==2.8.1")


@task
def tests():
    import subprocess

    subprocess.run("nosetests -v --with-coverage --cover-html")


@task
def build_exe():
    from PyInstaller.__main__ import run

    for script in ["synchronizer.spec"]:
        run([script, "--onefile", "--icon=icon.ico"])
