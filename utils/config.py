from ipaddress import ip_address
import os
import yaml
import argparse

from copy import deepcopy

from utils.structs import SingletonMeta
from utils.logger import Logger
import utils.helpers as helpers

BASE_PATH = os.path.abspath(os.path.dirname(__file__))


class Config(metaclass=SingletonMeta):
    def __init__(
        self,
        path=os.path.join(
                os.path.dirname(BASE_PATH),
                'config',
                'default.yaml'
            ),
        overriding_config=dict()
    ):

        self.config = {
            'config': path,
            'log_path': os.path.join(
                os.path.dirname(BASE_PATH),
                'log',
                'log.log'
            )
        }

        parser = argparse.ArgumentParser()

        parser.add_argument('--config', type=str)
        parser.add_argument('--log_path', type=str)
        parser.add_argument('--exp_path', type=str)
        parser.add_argument('--override', type=str, default=None)

        xargs = vars(parser.parse_args())
        xconfig = {k: v for k, v in xargs.items() if v is not None}

        self.config.update(xconfig)

        with open(self.config['config'], 'r') as f:
            self.config.update(yaml.safe_load(f))

        if (not overriding_config) and xconfig.get('override'):
            with open(xconfig['override'], 'r') as f:
                overriding_config = yaml.safe_load(f)

        self.override(self.config, overriding_config)
        self.config.update(xconfig)

        self.config_dict = deepcopy(self.config)

        for k, v in self.config.items():
            if isinstance(v, dict):
                self.config[k] = helpers.convert_dict_to_namespace(v)

        self.__dict__.update(self.config)

        if not os.path.isabs(self.exp_path):
            self.exp_path = os.path.join(
                os.path.dirname(BASE_PATH),
                self.exp_path
            )

        if not os.path.isabs(self.log_path):
            self.log_path = os.path.join(
                os.path.dirname(BASE_PATH),
                self.log_path
            )

        if not os.path.isdir(self.exp_path):
            os.mkdir(self.exp_path)

    def __call__(self):
        return self.config_dict

    def override(self, config, override_config):
        for k in (override_config.keys() - config.keys()):
            config[k] = override_config[k]

        for k, v in config.items():
            if isinstance(override_config, dict) and k in override_config:
                if isinstance(v, dict):
                    self.override(config[k], override_config[k])
                else:
                    config[k] = override_config[k]

    def save(self, path=None):
        if path is None:
            path = os.path.join(self.exp_path, self.config.split('/')[-1])

        with open(path, 'w') as fp:
            yaml.dump(self.config_dict, fp)


Logger(filename=Config().log_path).get()
