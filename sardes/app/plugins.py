# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import importlib
import os
import os.path as osp


def get_sardes_plugin_module_loaders(plugin_paths):
    """
    Return a dict containing sardes plugin module loaders from the specified
    list of paths.
    """
    if not isinstance(plugin_paths, (tuple, list)):
        plugin_paths = (plugin_paths,)
    plugin_paths = (path for path in plugin_paths if osp.isdir(path))

    module_loaders = {}
    for plugin_path in plugin_paths:
        for module_name in os.listdir(plugin_path):
            if not osp.isdir(osp.join(plugin_path, module_name)):
                continue
            if module_name in module_loaders:
                continue

            module_spec = importlib.machinery.PathFinder.find_spec(
                module_name, [plugin_path])
            if module_spec:
                source = module_spec.loader.get_source(module_name)
                if 'SARDES_PLUGIN_CLASS' in source:
                    module_loaders[module_name] = module_spec.loader

    return module_loaders


if __name__ == '__main__':
    from sardes import __rootdir__
    from sardes.config.main import CONFIG_DIR

    sardes_plugin_path = osp.join(__rootdir__, 'plugins')
    user_plugin_path = osp.join(CONFIG_DIR, 'plugins')
    if not osp.isdir(user_plugin_path):
        os.makedirs(user_plugin_path)

    print(get_sardes_plugin_module_loaders(sardes_plugin_path))
    print(get_sardes_plugin_module_loaders(user_plugin_path))
