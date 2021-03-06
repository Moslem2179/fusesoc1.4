import argparse
import os
import shutil
import sys

if sys.version_info[0] >= 3:
    import urllib.request as urllib
    from urllib.error import URLError
    from urllib.error import HTTPError
else:
    import urllib
    from urllib2 import URLError
    from urllib2 import HTTPError

from fusesoc.config import Config
from fusesoc.coremanager import CoreManager
from fusesoc.utils import pr_info

class FileAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        path = os.path.expandvars(values[0])
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        setattr(namespace, self.dest, [path])

class EdaTool(object):

    def __init__(self, system):
        config = Config()
        self.system = system
        self.build_root = os.path.join(config.build_root, self.system.name)
        self.src_root = os.path.join(self.build_root, 'src')

        self.cm = CoreManager()
        self.cores = self.cm.get_depends(self.system.name)

        self.env = os.environ.copy()
        self.env['BUILD_ROOT'] = os.path.abspath(self.build_root)

    def configure(self, args):
        if os.path.exists(self.work_root):
            for f in os.listdir(self.work_root):
                if os.path.isdir(os.path.join(self.work_root, f)):
                    shutil.rmtree(os.path.join(self.work_root, f))
                else:
                    os.remove(os.path.join(self.work_root, f))
        else:
            os.makedirs(self.work_root)

        for name in self.cores:
            pr_info("Preparing " + name)
            core = self.cm.get_core(name)
            dst_dir = os.path.join(Config().build_root, self.system.name, 'src', name)
            try:
                core.setup()
            except URLError as e:
                raise RuntimeError("Problem while fetching '" + core.name + "': " + str(e.reason))
            except HTTPError as e:
                raise RuntimeError("Problem while fetching '" + core.name + "': " + str(e.reason))
            core.export(dst_dir)

    def parse_args(self, args, prog, paramtypes):
        typedict = {'bool' : {'action' : 'store_true'},
                    'file' : {'type' : str , 'nargs' : 1, 'action' : FileAction},
                    'int'  : {'type' : int , 'nargs' : 1},
                    'str'  : {'type' : str , 'nargs' : 1},
                    }
        progname = 'fusesoc {} {}'.format(prog,
                                          self.system.name)
        parser = argparse.ArgumentParser(prog = progname,
                                         conflict_handler='resolve')
        for name in self.cores:
            core = self.cm.get_core(name)

            for param_name, param in core.parameter.items():
                if param.paramtype in paramtypes and \
                   (name == self.system.name or \
                   param.scope == 'public'):
                    parser.add_argument('--'+param_name,
                                        help=param.description,
                                        **typedict[param.datatype])

        p = parser.parse_args(args)

        for paramtype in ['plusarg',
                          'vlogparam']:
            setattr(self, paramtype, {})
            for key,value in vars(p).items():
                if value == True:
                    getattr(self, paramtype)[key] = "true"
                elif value == False or value is None:
                    pass
                else:
                    getattr(self, paramtype)[key] = str(value[0])

