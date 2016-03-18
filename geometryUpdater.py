# -*- coding: utf-8 -*-
"""
/***************************************************************************
 geometryUpdater
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
import timeit
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QObject, SIGNAL
from PyQt4.QtGui import QAction, QIcon, QMessageBox,QApplication

from qgis.core import QgsMapLayerRegistry,QgsVectorDataProvider
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from geometryUpdater_dialog import geometryUpdaterDialog
from result_dialog import  resultDialog
from updater import *
import os.path


class geometryUpdater(object):
    def __init__(self, iface):
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'geometryUpdater_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.wkbText = {0:"GeometryUnknown", 1:"Point", 3:"LineString", 4:"Polygon", 5:"MultiPoint", 6:"MultiLineString",
                        7:"MultiPolygon", 8:"NoGeometry", 9:"Point25D", 10:"LineString25D", 11:"Polygon25D",
                        12:"MultiPoint25D", 13:"MultiLineString25D", 14:"MultiPolygon25D", 100:"NoGeometry"}

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Geometry Updater')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'geometryUpdater')
        self.toolbar.setObjectName(u'geometryUpdater')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('geometryUpdater', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/geometryUpdater/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Geometry Updater'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def process(self):
        if len(self.allVectorLayers) > 1:
            #getting layers
            self.targetLayer = self.allVectorLayers[self.dlg.cmbTargetLayer.currentIndex()]
            self.sourceLayer = self.allVectorLayers[self.dlg.cmbSourceLayer.currentIndex()]
            openedAttrWindow = False #This variable is used for detecting opened attribute windows. During loading operation, opened windows make qgis crashed (maybe a bug)
            #so they must be closed
            for dialog in QApplication.instance().allWidgets():
                #I noticed that in my laptop getting all Qt widget's (in QGIS) names give error. But no problem with desktop. Here is try-except ;)
                try:
                    if dialog.objectName() in [u'QgsAttributeTableDialog', u'AttributeTable']:
                        openedAttrWindow = True
                except:
                    pass

            if openedAttrWindow:
                QMessageBox.warning(None,u'Notification', u'Please close all attribute windows to start the process.')

            else:
                #checking target and source layers must not be in editing mode.
                if not self.targetLayer.isEditable() and not self.sourceLayer.isEditable():
                    # checking for targetLayer editing capability.
                    isEditable = self.targetLayer.dataProvider().capabilities() & QgsVectorDataProvider.AddFeatures
                    if isEditable:
                        # checking targetLayer and sourceLayer are not same
                        if self.targetLayer.extent() != self.sourceLayer.extent() or self.targetLayer.publicSource() != self.sourceLayer.publicSource():
                            # checking layers geometry types
                            if self.targetLayer.geometryType() == self.sourceLayer.geometryType():
                                #if code can pass all conditions it means everything is fine ;) so we can start the process
                                #getting field names
                                targetKeyColumnName = self.targetLayer.dataProvider().fields().toList()[self.dlg.cmbTargetField.currentIndex()].name()
                                sourceKeyColumnName = self.sourceLayer.dataProvider().fields().toList()[self.dlg.cmbSourceField.currentIndex()].name()

                                self.parser = layer2Dict()#this thread class is used for generating feature dictionaries
                                #gui issues
                                self.dlg.btnStop.clicked.connect(self.parser.stop)
                                self.dlg.btnStart.setEnabled(False)
                                self.dlg.btnStop.setEnabled(True)
                                self.iface.mapCanvas().setRenderFlag(False)#qgis can crash in case of big geometry changes.to prevent
                                                                            #this issue disable rendering during process


                                self.parser.addJob(self.targetLayer,targetKeyColumnName)
                                self.parser.addJob(self.sourceLayer,sourceKeyColumnName)

                                #handling signals from qthread class
                                QObject.connect(self.parser,SIGNAL('progressLength'), self.setProgressLength)
                                QObject.connect(self.parser,SIGNAL('progress'), self.setProgress)
                                QObject.connect(self.parser,SIGNAL('status'), self.setStatus)
                                QObject.connect(self.parser,SIGNAL('error'), self.error)
                                QObject.connect(self.parser,SIGNAL("finish"), self.parseDone)
                                self.parser.start()
                                self.start_time = timeit.default_timer()#for calculating total run time
                            else:
                                QMessageBox.warning(self.dlg, u' Error',u'The layers geometry types have to be same to start the process.')
                        else:
                            QMessageBox.warning(self.dlg, u' Error', u'Target Layer and Source Layer must be different.')
                    else:
                        QMessageBox.warning(self.dlg, u' Error', u'Target Layer does not support editing.')
                else:
                    QMessageBox.warning(self.dlg, u' Error', u'Target Layer and Source Layer must not be in editing mode.')
        else:
            QMessageBox.warning(self.dlg, u' Error', u'There must be at least two vector layers added in QGIS canvas.')

    def setProgress(self, val):
        self.dlg.progressBar.setValue(val)

    def setProgressLength(self, val):
        self.dlg.progressBar.setMaximum(val)
        # if val==0:
        #     self.dlg.btnStop.setEnabled(False)

    def setStatus(self,message):
        self.dlg.lblStatus.setText(message)

    def error(self, exception):
        QMessageBox.critical(self.dlg,' Error', str(exception) + ' Operation was canceled.')

    def onStop(self):
        #this function is used when thread operation finished
        self.dlg.progressBar.reset()
        self.dlg.progressBar.setMaximum(1)
        self.dlg.lblStatus.clear()
        self.dlg.btnStart.setEnabled(True)
        self.dlg.btnStop.setEnabled(False)
        self.iface.mapCanvas().setRenderFlag(True)
        self.iface.mapCanvas().refresh()
        try:
            self.parser.terminate()
            self.committer.terminate()
            del self.parser
            del self.committer
        except:
            pass

    def parseDone(self):
        #this function updates geometries.
        if self.parser.hasError == False:
            if self.parser.isCancel == False:
                self.dlg.btnStop.setEnabled(False)#if the process comes to this stage, user can not cancel it.
                targetLayerDict = self.parser.featureDicts[0] #In process function i added targetLayer as first job so
                sourceLayerDict = self.parser.featureDicts[1] #the first element of the result list is targetDict other is sourceDict
                self.committer = Committer() #this class is used for saving changes to layers.
                self.dlg.progressBar.setMaximum(len(targetLayerDict))
                self.dlg.lblStatus.setText('Updating geometries...')
                self.targetLayer.startEditing()
                progress = 0
                for keyid in sourceLayerDict:
                    progress+=1
                    self.dlg.progressBar.setValue(progress)
                    if targetLayerDict.has_key(keyid):
                        self.targetLayer.changeGeometry(targetLayerDict[keyid].id(), sourceLayerDict[keyid].geometry())
                self.committer.setOptions(self.targetLayer)
                QObject.connect(self.committer, SIGNAL('commitStarted'), self.commitStarted)
                QObject.connect(self.committer, SIGNAL('finish'), lambda: self.commitFinished(self.targetLayer))
                self.committer.run()
            else:
                self.resultGenerator(['Operation was canceled by user. All changes were rollbacked.'])
                self.onStop()
        else:
            self.onStop()


    def commitStarted(self):
        self.dlg.lblStatus.setText(u'Please wait while saving changes to the datasource...')
        self.dlg.progressBar.setMaximum(0)
        self.dlg.btnStop.setEnabled(False)

    def commitFinished(self,targetLayer):
        self.onStop()
        self.resultGenerator(self.targetLayer.commitErrors())

    def resultGenerator(self, commitErrorList):
        self.resultDlg.textEdit.clear()
        total_run_time = '<p></p><b>Total execution time is %.2f seconds.</b><p></p>' % (timeit.default_timer()-self.start_time)
        self.resultDlg.textEdit.append(total_run_time) #First line is total tun time information
        for errorString in commitErrorList:
            self.resultDlg.textEdit.append(errorString)
        self.resultDlg.exec_()

    def onChangeLayerComboBox(self, cmbLayer, cmbAttr):
        #this function fills field comboboxes
        if self.allMapLayers:
            cmbAttr.clear() #clear
            targetVectorLayer = self.allMapLayers[cmbLayer.currentIndex()][1]
            attributes = targetVectorLayer.dataProvider().fields().toList()
            for attribute in attributes:
                cmbAttr.addItem(attribute.name() + ' (%s)' %(attribute.typeName()))

    def run(self):
        self.dlg = geometryUpdaterDialog()
        self.dlg.setFixedSize(self.dlg.size())
        self.resultDlg = resultDialog()
        self.resultDlg.setFixedSize(self.resultDlg.size())
        self.allVectorLayers = []

        self.allMapLayers = QgsMapLayerRegistry.instance().mapLayers().items() #this dict holds all map layer
        for (notImportantForNow, layerObj) in self.allMapLayers:
            if layerObj.type() == 0:
                self.allVectorLayers.append(layerObj)
                cmbLabel = layerObj.name() + ' (%d) (%s)' % (layerObj.featureCount(), self.wkbText[layerObj.wkbType()])
                self.dlg.cmbTargetLayer.addItem(cmbLabel)
                self.dlg.cmbSourceLayer.addItem(cmbLabel)

        #filling layer comboboxes
        self.onChangeLayerComboBox(self.dlg.cmbSourceLayer, self.dlg.cmbSourceField)
        self.dlg.cmbSourceLayer.currentIndexChanged.connect(lambda: self.onChangeLayerComboBox(self.dlg.cmbSourceLayer, self.dlg.cmbSourceField))
        self.onChangeLayerComboBox(self.dlg.cmbTargetLayer, self.dlg.cmbTargetField)
        self.dlg.cmbTargetLayer.currentIndexChanged.connect(lambda: self.onChangeLayerComboBox(self.dlg.cmbTargetLayer, self.dlg.cmbTargetField))

        self.dlg.btnStart.clicked.connect(self.process)
        self.dlg.btnStop.setEnabled(False)
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if not result:
            try:
                self.parser.stop()
                self.committer.terminate()
                del self.loader
                del self.committer
            except:
                pass
