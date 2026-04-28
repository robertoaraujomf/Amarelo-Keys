#!/usr/bin/env python3
"""Generate Amarelo Keys application icon"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt5.QtCore import Qt, QRect

def create_icon():
    app = QApplication([])
    
    sizes = [16, 32, 48, 64, 128, 256]
    icon = QIcon()
    
    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background circle
        margin = size // 8
        rect = QRect(margin, margin, size - 2*margin, size - 2*margin)
        painter.setBrush(QBrush(QColor("#FFD700")))
        painter.setPen(QPen(QColor("#B8860B"), max(2, size//32)))
        painter.drawEllipse(rect)
        
        # Keyboard key shape
        key_margin = size // 3
        key_rect = QRect(key_margin, key_margin, size - 2*key_margin, size - 2*key_margin)
        painter.setBrush(QBrush(QColor("#1a2332")))
        painter.setPen(QPen(QColor("#FFD700"), max(1, size//40)))
        painter.drawRoundedRect(key_rect, size//10, size//10)
        
        # "A" letter to represent a key
        font = QFont("Arial", size//3, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#FFD700"), max(1, size//40)))
        painter.drawText(key_rect, Qt.AlignCenter, "A")
        
        painter.end()
        icon.addPixmap(pixmap)
    
    # Save as PNG
    icon.pixmap(256, 256).save("/home/roberto/Projetos/Amarelo-Keys/icons/amarelo-keys.png")
    
    # Also create a simpler version for tray (smaller, flat)
    tray_pixmap = QPixmap(64, 64)
    tray_pixmap.fill(Qt.transparent)
    painter = QPainter(tray_pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor("#FFD700")))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(8, 8, 48, 48, 8, 8)
    painter.setPen(QPen(QColor("#1a2332"), 3))
    painter.setFont(QFont("Arial", 28, QFont.Bold))
    painter.drawText(QRect(8, 8, 48, 48), Qt.AlignCenter, "K")
    painter.end()
    tray_pixmap.save("/home/roberto/Projetos/Amarelo-Keys/icons/tray-icon.png")
    
    print("Icons created successfully!")
    print("Main icon: icons/amarelo-keys.png")
    print("Tray icon: icons/tray-icon.png")

if __name__ == "__main__":
    create_icon()
