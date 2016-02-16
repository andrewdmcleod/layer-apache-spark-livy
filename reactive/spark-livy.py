# pylint: disable=unused-argument
from charms.reactive import when, when_not
from charms.reactive import set_state, remove_state
from charmhelpers.core import hookenv
from charms.livy import Livy
from charms.hadoop import get_dist_config


dist = get_dist_config()
livy = Livy(dist)


@when('spark.available')
@when_not('livy.installed')
def install_livy(hadoop):
    if livy.verify_resources():
        hookenv.status_set('maintenance', 'Installing Livy')
        livy.install()
        set_state('livy.installed')


@when('livy.installed', 'spark.available')
@when_not('livy.started')
def configure_livy(spark):
    hookenv.status_set('maintenance', 'Setting up Livy')
    livy.setup_livy()
    livy.configure_livy()
    livy.start()
    livy.open_ports()
    set_state('livy.started')
    hookenv.status_set('active', 'Ready')


@when('livy.started')
@when_not('spark.available')
def stop_livy():
    livy.stop()
    remove_state('livy.started')


@when_not('spark.related')
def report_blocked():
    hookenv.status_set('blocked', 'Waiting for relation to Apache Spark')


@when('spark.related')
@when_not('spark.available')
def report_waiting(spark):
    hookenv.status_set('waiting', 'Waiting for Apache Spark to become ready')
