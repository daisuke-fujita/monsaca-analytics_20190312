import copy
import json
import logging

from main.config import const as config_const
from main.dsl import const as dsl_const
from main.dsl import dsl
from main.dsl import parser
from main.exception import dsl as err
import main.util.common_util as cu

logger = logging.getLogger(__name__)


class DSLInterpreter():

    def __init__(self):
        self.file_in_use = None
        self.dsl = dsl.MonanasDSL()
        self.mappings = {}

    def execute_string(self, str_program):
        """Parse and execute the command/s in the string passed as parameter

        :param str_program: str -- command to be executed
        :returns: str -- execution result
        """
        info = parser.get_parser().parseString(str_program)
        return self.execute(info)

    def execute_file(self, file_program):
        """Parse and execute the command/s in the file passed as parameter

        :param file_program: str -- path to the file containing the
        command to be executed
        :returns: str -- execution result
        """
        info = parser.get_parser().parseFile(file_program)
        return self.execute(info)

    def execute(self, info):
        """Execute parsed command/s

        :param info: dict -- containing the parsed instructions
        :returns: str -- execution result
        """
        for cmd in info:
            for key in cmd.keys():
                if key == dsl_const.CREATE:
                    return self.create(cmd[key][0], cmd[key][1])
                elif key == dsl_const.CONNECT:
                    return self.connect(cmd[key][0], cmd[key][1])
                elif key == dsl_const.DISCONNECT:
                    return self.disconnect(cmd[key][0], cmd[key][1])
                elif key == dsl_const.LOAD:
                    return self.load(cmd[key][0])
                elif key == dsl_const.SAVE_AS:
                    return self.save(cmd[key][0])
                elif key == dsl_const.SAVE:
                    return self.save()
                elif key == dsl_const.REMOVE:
                    return self.remove(cmd[key][0])
                elif key == dsl_const.MODIFY:
                    return self.modify(
                        cmd[key][0], cmd[key][1:-1], cmd[key][-1])
                elif key == dsl_const.PRINT:
                    if len(cmd[key]) > 0:
                        return self.prnt(cmd[key][0])
                    else:
                        return self.prnt_all()
                elif key == dsl_const.LIST:
                    if len(cmd[key]) > 0:
                        return self.list(cmd[key][0])
                    else:
                        return self.list_all()
                elif key == dsl_const.HELP:
                    return self.help()
                else:
                    return logger.warn("Wrong command" + str(cmd))

    def create(self, varname, modulename):
        """Add a module defined by modulename in the configuration

        :param varname: str -- name of the variable representing
        the new component
        :returns: str -- new component ID
        """
        clz = cu.get_class_by_name(modulename)
        conf = copy.deepcopy(clz.get_default_config())
        comp_id = self.dsl.add_component(conf)
        self.mappings[varname] = comp_id
        return comp_id

    def connect(self, origin_varname, dest_varname):
        """Connect two components

        :param origin_varname: str -- variable name or ID of the source
        component of the connection
        :param dest_varname: str -- variable name or ID of the destination
        component of the connection
        :returns: bool -- True if the connection was performed,
        false otherwise
        """
        origin_id = self._get_id(origin_varname)
        dest_id = self._get_id(dest_varname)
        return self.dsl.connect_components(origin_id, dest_id)

    def _get_id(self, name_or_id):
        """Get the ID from a name or ID

        :param name_or_id: str -- variable name or ID
        :param dest_varname: variable name or ID of the destination
        component of the connection
        :returns: str -- ID
        """
        if name_or_id in self.mappings.keys():
            return self.mappings[name_or_id]
        for comp_type in config_const.components_types:
            if name_or_id in self.dsl._config[comp_type]:
                return name_or_id
        raise err.DSLInterpreterException("undefined variable: " + name_or_id)

    def disconnect(self,  origin_varname, dest_varname):
        """Disconnect two components

        :param origin_varname: str -- variable name or ID of the source
        component of the connection
        :param dest_varname: str -- variable name or ID of the destination
        component of the connection
        :returns: bool -- True if the components were disconnected,
        false otherwise
        """
        origin_id = self._get_id(origin_varname)
        dest_id = self._get_id(dest_varname)
        return self.dsl.disconnect_components(origin_id, dest_id)

    def load(self, filepath):
        """Load configuration from a file

        :param filepath: str -- path to the file to be loaded
        """
        self.dsl.load_configuration(filepath)
        self.file_in_use = filepath

    def save(self, filepath=None):
        """Save configuration to a file

        :param filepath: str -- (Optional) path to the file where the
        configuration will be saved. If the path is not provided, the last file
        used for saving or loading will be used.
        """
        if not filepath:
            filepath = self.file_in_use
        saved = self.dsl.save_configuration(filepath, overwrite_file=True)
        if saved:
            self.file_in_use = filepath
        return saved

    def remove(self, varname):
        """Remove a variable or ID from the configuration

        :param varname: str -- variable name or ID mapped to the component
        that will be removed from the configuration
        """
        remove_id = self._get_id(varname)
        return self.dsl.remove_component(remove_id)

    def modify(self, varname, params, value):
        """Override the value of the configuration path of a component

        :param varname: str -- variable name or ID mapped to the component
        :param params: list -- path to be modified in the configuration
        :param value: any -- value to assign
        """
        modify_id = self._get_id(varname)
        return self.dsl.modify_component(modify_id, params, value)

    def prnt(self, varname):
        """Print the configuration of the module/s defined by varname

        If varname is a variable or ID associated to a particular component,
        the configuration of that component will be printed. If if is a type
        of components, the configurations of all components of that type
        will be printed.

        :param varname: str -- variable, ID or type to be printed
        :returns: str -- requested configuration in string format
        """
        if varname in self.dsl._config.keys():
            return self._json_print(self.dsl._config[varname])
        itemId = self._get_id(varname)
        for k in config_const.components_types:
            if itemId in self.dsl._config[k]:
                return self._json_print(self.dsl._config[k][itemId])

    def prnt_all(self):
        """Print the the whole configuration

        :returns: str -- whole configuration in string format
        """
        return self._json_print(self.dsl._config)

    def _json_print(self, jstr):
        """Format Json as a clean string"""
        return json.dumps(jstr, indent=4, separators=(',', ': '))

    def list(self, key):
        """List the available components of the type passed as parameter"""
        ret = ""
        if key in config_const.components_types:
            for name in cu.get_available_class_names(key):
                ret += "- " + name + "\n"
        return ret

    def list_all(self):
        """List all available components grouped by type"""
        ret = ""
        for key in config_const.components_types:
            ret += "- " + key + "\n"
            for name in cu.get_available_class_names(key):
                ret += "    - " + name + "\n"
        return ret

    def help(self):
        return """
Available commands
    - print: prints current configuration
    - list: shows available modules
    - load: loads a config from a file
    - save: saves a config to a file
    - <var> = <module>: instantiates module <module>, referenced by <var>
    - <var1>-><var2>: connects the module <var1> to the module <var2>
    - <var1>!-><var2>: disconnects the module <var1> from the module <var2>
    - rm <var>: removes the module corresponding to <var>
    - exit: finishes the execution of monanas command line
"""
