# -*- coding: utf-8 -*-
"""
/***************************************************************************
 geometryUpdater
                                 A QGIS plugin
 Updates a vector layer's features geometry from another vector layer by using ID
                             -------------------
        begin                : 2016-03-02
        copyright            : (C) 2016 by Mehmet Selim BILGIN
        email                : mselimbilgin@yahoo.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load geometryUpdater class from file geometryUpdater.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .geometryUpdater import geometryUpdater
    return geometryUpdater(iface)
