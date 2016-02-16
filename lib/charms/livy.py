import os
import jujuresources

from path import Path
from jujubigdata import utils
from subprocess import call
from charmhelpers.core import unitdata, hookenv


class Livy(object):
    """
    This class manages the Livy deployment steps.

    :param DistConfig dist_config: The configuration container object needed.
    """
    def __init__(self, dist_config):
        self.dist_config = dist_config
        self.cpu_arch = utils.cpu_arch()

        self.resources = {
            'livy': 'livy-%s' % self.cpu_arch,
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())


    def is_installed(self):
        return unitdata.kv().get('livy.prepared')


    def install(self, force=False):
        '''
        Create the directories. This method is to be called only once.

        :param bool force: Force the execution of the installation even if this is not the first installation attempt.
        '''
        if not force and self.is_installed():
            return

        jujuresources.install(self.resources['livy'],
                              destination=self.dist_config.path('livy'),
                              skip_top_level=True)
        self.dist_config.add_dirs()
        self.dist_config.add_users()
        self.dist_config.add_packages()

        unitdata.kv().set('livy.prepared', True)
        unitdata.kv().flush(True)


    def setup_livy(self):
        self.setup_livy_config()


    def setup_livy_config(self):
        '''
        copy the default configuration files to livy_conf property
        '''
        default_conf = self.dist_config.path('livy') / 'conf'
        livy_conf = self.dist_config.path('livy_conf')
        livy_conf.rmtree_p()
        default_conf.copytree(livy_conf)


    def configure_livy(self):
        '''
        Configure livy environment for all users
        '''
        livy_bin = self.dist_config.path('livy') / 'bin'
        with utils.environment_edit_in_place('/etc/environment') as env:
            if livy_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], livy_bin])
            hadoop_cp = '/etc/hadoop/conf:/usr/lib/hadoop/share/hadoop/common/lib/*:/usr/lib/hadoop/share/hadoop/common/*\
:/usr/lib/hadoop/share/hadoop/hdfs:/usr/lib/hadoop/share/hadoop/hdfs/lib/*\
:/usr/lib/hadoop/share/hadoop/hdfs/*:/usr/lib/hadoop/share/hadoop/yarn/lib/*\
:/usr/lib/hadoop/share/hadoop/yarn/*:/usr/lib/hadoop/share/hadoop/mapreduce/lib/*\
:/usr/lib/hadoop/share/hadoop/mapreduce/*:/usr/lib/hadoop/contrib/capacity-scheduler/*.jar'
            env['CLASSPATH'] = hadoop_cp

        cmd = "chown -R hue:hadoop {}".format(self.dist_config.path('livy'))
        call(cmd.split())
        cmd = "chown -R hue:hadoop {}".format(self.dist_config.path('livy_conf'))
        call(cmd.split())

    def start(self):
        # Start if we're not already running. We currently dont have any
        # runtime config options, so no need to restart when hooks fire.
        if not utils.jps("livy"):
            livy_log = self.dist_config.path('livy_logs') + 'livy-server.log'
            livy_home = self.dist_config.path('livy')
            # chdir here because things like zepp tutorial think ZEPPELIN_HOME
            # is wherever the daemon was started from.
            os.chdir(livy_home)
            utils.run_as('hue', './bin/livy-server', '2>&1', livy_log, '&' )

    def stop(self):
        livy_conf = self.dist_config.path('livy_conf')
        livy_home = self.dist_config.path('livy')
        # TODO: try/catch existence of livy-daemon.sh. Stop hook will fail
        # if we try to destroy a deployment that didn't finish installing.
        utils.run_as('hue', 'pkill', '-9', '-u', 'hue')

    def open_ports(self):
        for port in self.dist_config.exposed_ports('livy'):
            hookenv.open_port(port)
  
    def close_ports(self):
        for port in self.dist_config.exposed_ports('livy'):
            hookenv.close_port(port)
  
    def cleanup(self):
        self.dist_config.remove_dirs()
        unitdata.kv().set('livy.installed', False)

