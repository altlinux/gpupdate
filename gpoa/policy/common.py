from enum import Enum

class Perms (Enum):
    USER = 1
    ROOT = 2

class Policy (object):
    @property
    def name(self):
        try:
            return self.__name
        except AttributeError as e:
            raise e

    @property
    def script_name(self):
        try:
            return self.__script_name
        except AttributeError as e:
            raise e

    @property
    def template(self):
        try:
            return self.__template
        except AttributeError as e:
            raise e

    @property
    def data_roots(self):
        try:
            return self.__data_roots
        except AttributeError as e:
            raise e

    @property
    def perms(self):
        try:
            return self.__perms
        except AttributeError as e:
            raise e

    def process(self, scope, path):
        raise "process must be implemented in child class"
