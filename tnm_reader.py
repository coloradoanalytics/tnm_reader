import os
from qgis.PyQt import QtWidgets, QtGui, QtCore
from qgis.core import (
    QgsProject, 
    QgsVectorLayer, 
    QgsField, 
    QgsPointXY, 
    QgsGeometry, 
    QgsFeature, 
    Qgis,
    QgsCoordinateReferenceSystem
)
from qgis.gui import QgsMessageBar
import xml.etree.ElementTree as ET
from .tnm_reader_dialog import TNMReaderDialog
from PyQt5.QtCore import QCoreApplication, QVariant

class TNMReader:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg = TNMReaderDialog()
        self.actions = []
        self.menu = self.tr(u'&TNM Reader')

    def initGui(self):
        icon_path = ':/plugins/tnm_reader/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'TNM Reader'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&TNM Reader'), action)
            self.iface.removeToolBarIcon(action)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        parent=None,
        enabled=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        shortcut=None
    ):
        icon = QtGui.QIcon(icon_path)
        action = QtWidgets.QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled)

        if status_tip:
            action.setStatusTip(status_tip)

        if whats_this:
            action.setWhatsThis(whats_this)

        if shortcut:
            action.setShortcut(shortcut)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        self.actions.append(action)
        return action

    def run(self):
        self.dlg.show()
        result = self.dlg.exec_()
        if result == 1:
            print("OK button clicked")  # Debugging output
            self.read_tnm_file()

    def read_tnm_file(self):
        file_path = self.dlg.lineEdit.text()
        print(f"File path: {file_path}")  # Debugging output
        if not os.path.exists(file_path):
            self.iface.messageBar().pushMessage("Error", "File does not exist", level=Qgis.Critical)
            return

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            receivers_element = root.find("receivers")
            if receivers_element is None:
                self.iface.messageBar().pushMessage("Error", "No receivers found in the file", level=Qgis.Critical)
                return

            levels = {}
            additional = []

            for receiver in receivers_element.findall("receiver"):
                name = receiver.find("name").text
                points = receiver.find("points")
                point = points.find("point")
                x = float(point.find("theX").text)
                y = float(point.find("theY").text)
                z = float(point.find("theZ").text)

                receiver_results = receiver.find("ReceiverResults")
                if receiver_results is None:
                    continue

                for receiver_result in receiver_results.findall("ReceiverResult"):
                    calculated = receiver_result.find("Calculated").text.lower() == 'true'
                    if not calculated:
                        continue

                    receiver_name = receiver_result.find("Name").text
                    with_barrier_level = float(receiver_result.find("WithBarrierLevel").text)
                    no_barrier_level = float(receiver_result.find("NoBarrierLevel").text)
                    noise_reduction_difference = float(receiver_result.find("NoiseReductionDifference").text)

                    level_key = "additional"
                    if "_level_" in receiver_name:
                        level_key = receiver_name.split("_level_")[-1]

                    result = {
                        'name': receiver_name.replace(f"_level_{level_key}", ""),
                        'x': x,
                        'y': y,
                        'z': z,
                        'with_barrier_level': with_barrier_level,
                        'no_barrier_level': no_barrier_level,
                        'noise_reduction_difference': noise_reduction_difference
                    }

                    if level_key not in levels:
                        levels[level_key] = []

                    levels[level_key].append(result)

            for level_key, results in levels.items():
                if level_key == "additional":
                    layer_name = "Results"
                else:
                    layer_name = f"Results Level {level_key}"

                layer = self.create_results_layer(layer_name, results)
                QgsProject.instance().addMapLayer(layer)
                
                # Zoom to the extent of the new layer
                self.iface.mapCanvas().setExtent(layer.extent())
                self.iface.mapCanvas().refresh()

            print("Layers created successfully")  # Debugging output

        except Exception as e:
            self.iface.messageBar().pushMessage("Error", f"Failed to read the file: {e}", level=Qgis.Critical)
            print(f"Error: {e}")  # Debugging output

    def create_results_layer(self, layer_name, results):
        # Get the project CRS
        project_crs = QgsProject.instance().crs().authid()
        
        # Create a new point layer with the project CRS
        vl = QgsVectorLayer(f"Point?crs={project_crs}", layer_name, "memory")
        pr = vl.dataProvider()

        # Add the necessary fields
        pr.addAttributes([
            QgsField("name", QVariant.String),
            QgsField("with_barrier", QVariant.Double),
            QgsField("no_barrier", QVariant.Double),
            QgsField("noise_reduction", QVariant.Double)
        ])
        vl.updateFields()

        # Create features and add them to the layer
        features = []
        for result in results:
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(result['x'], result['y'])))
            fet.setAttributes([
                result['name'],
                result['with_barrier_level'],
                result['no_barrier_level'],
                result['noise_reduction_difference']
            ])
            features.append(fet)

        pr.addFeatures(features)
        vl.updateExtents()

        # Set the CRS of the layer explicitly to the project CRS
        vl.setCrs(QgsCoordinateReferenceSystem(project_crs))
        
        return vl

    def tr(self, message):
        return QCoreApplication.translate('TNMReader', message)
