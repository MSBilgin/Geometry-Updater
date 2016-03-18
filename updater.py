# -*- coding: utf-8 -*-
"""
/***************************************************************************
 updater
                                 A QGIS plugin
 Updates a vector layer's features geometry from another vector layer by using ID
                             -------------------
        copyright            : (C) 2016 by Mehmet Selim BILGIN
        email                : mselimbilgin@yahoo.com
        web                  : http://cbsuygulama.wordpress.com/
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

from PyQt4.QtCore import QThread, SIGNAL

class layer2Dict(QThread):
    #this thread is used for converting a layer's features to dict
    def __init__(self):
        QThread.__init__(self)
        self.jobs = []
        self.featureDicts = []
        self.isCancel = False
        self.hasError = False

    def addJob(self,qgsVectorLayer, keyColumn):
        self.jobs.append([qgsVectorLayer,keyColumn])

    def run(self):
        for job in self.jobs:
            try:
                if not self.isCancel:
                    dict = {}
                    layer = job[0]
                    keyField = job[1]
                    self.emit(SIGNAL('progressLength'), layer.featureCount())
                    self.emit(SIGNAL('status'), 'Generating feature dictionaries...')
                    progress = 0
                    for feature in layer.getFeatures():
                        if not self.isCancel:
                            dict[feature[keyField]] = feature
                            progress = progress+1
                            self.emit(SIGNAL('progress'), progress)
                        else:
                            self.featureDicts = []
                    self.featureDicts.append(dict)
            except Exception,err:
                self.hasError = True
                self.emit(SIGNAL('error'), err)
        self.emit(SIGNAL('finish'),True)

    def stop(self):
        self.isCancel = True
        self.wait()
        self.terminate()

class Committer(QThread):
    #this thread is used for handling long process of saving changes to datasource
    def __init__(self):
        QThread.__init__(self)
        self.qgsVectorLayer = None

    def setOptions(self, qgsVectorLayer):
        self.qgsVectorLayer = qgsVectorLayer

    def run(self):
        self.emit(SIGNAL("commitStarted"))
        self.qgsVectorLayer.commitChanges()
        self.emit(SIGNAL('finish'), True)