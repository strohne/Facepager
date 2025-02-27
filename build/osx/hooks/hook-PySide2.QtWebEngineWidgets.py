#-----------------------------------------------------------------------------
# Copyright (c) 2014-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks.qt import add_qt5_dependencies, pyside2_library_info
from PyInstaller.utils.hooks import remove_prefix, get_module_file_attribute, \
    collect_system_data_files
from PyInstaller.depend.bindepend import getImports
import PyInstaller.compat as compat

def get_relative_path_if_possible(actual, possible_prefix):
    actual_path = Path(actual)
    possible_prefix_path = Path(possible_prefix)
    try:
        return str(actual_path.relative_to(possible_prefix_path))
    except:
        return actual

# Ensure PySide2 is importable before adding info depending on it.
if pyside2_library_info.version:
    hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

    # Include the web engine process, translations, and resources.
    # According to https://bugreports.qt.io/browse/PYSIDE-642?focusedCommentId=461015&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-461015,
    # there's no subdir for windows
    rel_data_path = ['PySide2'] if sys.platform == 'win32' else ['PySide2', 'Qt']
    if compat.is_darwin:
        # This is based on the layout of the Mac wheel from PyPi.
        data_path = pyside2_library_info.location['DataPath']
        libraries = ['QtCore', 'QtWebEngineCore', 'QtQuick', 'QtQml', 'QtNetwork',
                     'QtGui', 'QtWebChannel', 'QtPositioning']
        for i in libraries:
            datas += collect_system_data_files(
                os.path.join(data_path, 'lib', i + '.framework'),
                os.path.join(*(rel_data_path + ['lib'])), True)
        datas += [(os.path.join(data_path, 'lib', 'QtWebEngineCore.framework',
                                'Resources'), os.curdir)]
    else:
        locales = 'qtwebengine_locales'
        resources = 'resources'
        datas += [
            # Gather translations needed by Chromium.
            (os.path.join(pyside2_library_info.location['TranslationsPath'], locales),
             os.path.join(*(rel_data_path + ['translations', locales]))),
            # Per the `docs <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html#deploying-resources>`_,
            # ``DataPath`` is the base directory for ``resources``.
            #
            # When Python 3.4 goes EOL (see `PEP 448`_, this is better written as
            # ``os.path.join(*rel_data_path, resources)``.
            (os.path.join(pyside2_library_info.location['DataPath'], resources),
             os.path.join(*(rel_data_path + [resources]))),
            # Include the webengine process. The ``LibraryExecutablesPath`` is only
            # valid on Windows and Linux.
            #
            # Again, rewrite when Python 3.4 is EOL to
            # ``os.path.join(*rel_data_path, remove_prefix(...``.
            (os.path.join(pyside2_library_info.location['LibraryExecutablesPath'],
                          'QtWebEngineProcess*'),
             os.path.join(*(rel_data_path +
                          [get_relative_path_if_possible(pyside2_library_info.location['LibraryExecutablesPath'],
                                        pyside2_library_info.location['PrefixPath'] + '/')])))
        ]
        if compat.is_win:
            datas += [x for x in collect_system_data_files(pyside2_library_info.location['PrefixPath'], 
                '.') if os.path.basename(x[0]) == 'qt.conf']


    # Add Linux-specific libraries.
    if compat.is_linux:
        # The automatic library detection fails for `NSS
        # <https://packages.ubuntu.com/search?keywords=libnss3>`_, which is used by
        # QtWebEngine. In some distributions, the ``libnss`` supporting libraries
        # are stored in a subdirectory ``nss``. Since ``libnss`` is not statically
        # linked to these, but dynamically loads them, we need to search for and add
        # them.
        #
        # First, get all libraries linked to ``PyQt5.QtWebEngineWidgets``.
        for imp in getImports(get_module_file_attribute('PySide2.QtWebEngineWidgets')):
            # Look for ``libnss3.so``.
            if os.path.basename(imp).startswith('libnss3.so'):
                # Find the location of NSS: given a ``/path/to/libnss.so``,
                # add ``/path/to/nss/*.so`` to get the missing NSS libraries.
                nss_subdir = os.path.join(os.path.dirname(imp), 'nss')
                if os.path.exists(nss_subdir):
                    binaries.append((os.path.join(nss_subdir, '*.so'), 'nss'))
