#!/usr/bin/env python3
"""
Amarelo Keys - Instalador com Interface Gráfica
Autor: Amarelo Keys Team
Versão: 1.0.0
"""

import os
import sys
import subprocess
import shutil
import stat
import platform
from pathlib import Path


APP_NAME = "Amarelo Keys"
APP_ID = "amarelo-keys"
VERSION = "1.0.0"
AUTHOR = "Amarelo Keys Team"

INSTALL_DIR = Path.home() / ".local" / "share" / APP_ID
DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / f"{APP_ID}.desktop"
AUTOSTART_FILE = Path.home() / ".config" / "autostart" / f"{APP_ID}.desktop"
MAIN_SCRIPT = Path(__file__).parent / "amarelo_keys.py"


try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QTextEdit, QProgressBar, QGroupBox,
        QCheckBox, QMessageBox, QScrollArea, QFrame, QTabWidget,
        QTableWidget, QTableWidgetItem, QSpacerItem, QSizePolicy,
        QApplication, QStyleFactory
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
    from PyQt5.QtGui import QColor, QPalette, QFont, QPainter, QBrush, QIcon, QPixmap, QLinearGradient, QGradient
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("=" * 50)
    print(f"{APP_NAME} - Instalador")
    print("=" * 50)
    print("\nPyQt5 não está instalado.")
    print("Execute um dos comandos abaixo para instalar:\n")
    print("  pip3 install PyQt5")
    print("  sudo apt install python3-pyqt5")
    print("\nOu use o script de instalação em modo texto:")
    print("  python3 install.py")
    print("=" * 50)
    input("\nPressione Enter para sair...")
    sys.exit(1)


class AnimatedWidget(QWidget):
    """Widget com animação de fade"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 1.0
        
    def setOpacity(self, value):
        self._opacity = max(0, min(1, value))
        self.update()
        
    def paintEvent(self, event):
        if self._opacity < 1.0:
            painter = QPainter(self)
            painter.setOpacity(self._opacity)
            super().paintEvent(event)


class InstallerThread(QThread):
    """Thread para instalação em background"""
    
    log = pyqtSignal(str, str)
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)
    step = pyqtSignal(int)
    
    def __init__(self, options):
        super().__init__()
        self.options = options
        self._is_running = True
        
    def run(self):
        try:
            self._install()
        except Exception as e:
            self.log.emit("error", f"Erro fatal: {str(e)}")
            self.finished.emit(False, str(e))
    
    def _log(self, msg, level="info"):
        self.log.emit(f"[{level.upper()}] {msg}", level)
        
    def _run(self, cmd, description="", check=True, sudo=False):
        self.progress.emit(description, -1)
        self._log(description, "info")
        
        if isinstance(cmd, str):
            if sudo and os.geteuid() != 0:
                cmd = f"sudo {cmd}"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True
            )
        else:
            if sudo and os.geteuid() != 0:
                cmd = ["sudo"] + cmd
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    self._log(line.strip(), "detail")
        
        if check and result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Erro desconhecido"
            self._log(error_msg, "error")
            raise Exception(error_msg)
        
        return result
    
    def _install(self):
        self._log("=" * 40, "info")
        self._log("INICIANDO INSTALAÇÃO", "info")
        self._log("=" * 40, "info")
        
        self.step.emit(0)
        
        if self.options.get('install_deps', True):
            self.progress.emit("Verificando sistema...", 5)
            self._check_system()
            
            self.progress.emit("Instalando dependências...", 15)
            self._install_dependencies()
        else:
            self.step.emit(20)
        
        self.progress.emit("Criando diretórios...", 40)
        self._create_directories()
        
        self.progress.emit("Instalando arquivos...", 55)
        self._install_files()
        
        if self.options.get('create_launcher', True):
            self.progress.emit("Criando lançador...", 70)
            self._create_launcher()
        
        if self.options.get('autostart', True):
            self.progress.emit("Configurando início automático...", 80)
            self._setup_autostart()
        
        if self.options.get('setup_permissions', True):
            self.progress.emit("Configurando permissões...", 90)
            self._setup_permissions()
        
        self.step.emit(100)
        self.progress.emit("Instalação concluída!", 100)
        self._log("=" * 40, "success")
        self._log("INSTALAÇÃO CONCLUÍDA COM SUCESSO!", "success")
        self._log("=" * 40, "success")
        self.finished.emit(True, "Instalação realizada com sucesso!")
    
    def _check_system(self):
        self._log(f"Sistema: {platform.system()} {platform.release()}", "info")
        self._log(f"Python: {sys.version.split()[0]}", "info")
        
        if platform.system() != "Linux":
            raise Exception("Este aplicativo só funciona em sistemas Linux")
        
        self.step.emit(10)
    
    def _install_dependencies(self):
        self._log("Instalando dependências...", "info")
        
        packages = [
            ("python3-pyqt5", "PyQt5"),
            ("python3-pip", "pip"),
        ]
        
        for pkg, name in packages:
            self._log(f"Verificando {name}...", "detail")
            result = subprocess.run(
                f"dpkg -l | grep -q 'ii  {pkg}'",
                shell=True, capture_output=True
            )
            if result.returncode != 0:
                self._log(f"Instalando {name}...", "info")
                try:
                    self._run(
                        f"apt-get install -y {pkg}",
                        f"Instalando {name}...",
                        sudo=True
                    )
                except Exception as e:
                    self._log(f"Fallback: usando pip para {name}", "warning")
                    self._run(
                        f"pip3 install {pkg.replace('python3-', '')} --quiet",
                        f"Instalando {name} via pip..."
                    )
            else:
                self._log(f"{name} já está instalado", "success")
        
        self._log("Instalando python-xlib...", "info")
        result = subprocess.run(
            f"{sys.executable} -c 'from Xlib import X'",
            shell=True, capture_output=True
        )
        if result.returncode != 0:
            self._run(
                f"pip3 install python-xlib --quiet",
                "Instalando python-xlib..."
            )
        else:
            self._log("python-xlib já está instalado", "success")
        
        self.step.emit(30)
    
    def _create_directories(self):
        self._log("Criando diretórios de instalação...", "info")
        
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        DESKTOP_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        self._log(f"Diretório: {INSTALL_DIR}", "detail")
        self._log(f"Desktop: {DESKTOP_FILE}", "detail")
        self._log(f"Autostart: {AUTOSTART_FILE}", "detail")
        
        self.step.emit(40)
    
    def _install_files(self):
        self._log("Copiando arquivos...", "info")
        
        if not MAIN_SCRIPT.exists():
            raise Exception(f"Arquivo principal não encontrado: {MAIN_SCRIPT}")
        
        dest = INSTALL_DIR / "amarelo_keys.py"
        shutil.copy2(MAIN_SCRIPT, dest)
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
        
        self._log(f"Copiado: {MAIN_SCRIPT} -> {dest}", "success")
        self.step.emit(60)
    
    def _create_launcher(self):
        self._log("Criando lançador (.desktop)...", "info")
        
        content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Acessibilidade para teclas defeituosas no Linux
Exec={sys.executable} {INSTALL_DIR / "amarelo_keys.py"}
Icon=input-keyboard
Terminal=false
Categories=Utility;Accessibility;System;
Keywords=keyboard;accessibility;keys;remap;defective;
StartupNotify=true
"""
        with open(DESKTOP_FILE, 'w') as f:
            f.write(content)
        
        self._log(f"Lançador criado: {DESKTOP_FILE}", "success")
        
        subprocess.run(
            f"gtk-update-icon-cache -f -t {Path.home() / '.local' / 'icons'} 2>/dev/null || true",
            shell=True
        )
    
    def _setup_autostart(self):
        self._log("Configurando início automático...", "info")
        
        content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Acessibilidade para teclas defeituosas
Exec={sys.executable} {INSTALL_DIR / "amarelo_keys.py"}
Icon=input-keyboard
Terminal=false
X-GNOME-Autostart-enabled=true
"""
        with open(AUTOSTART_FILE, 'w') as f:
            f.write(content)
        
        self._log(f"Autostart configurado: {AUTOSTART_FILE}", "success")
    
    def _setup_permissions(self):
        self._log("Configurando permissões X11...", "info")
        
        result = subprocess.run(
            "xhost +SI:localuser:root 2>&1",
            shell=True, capture_output=True, text=True
        )
        
        if result.returncode == 0:
            self._log("Permissões X11 configuradas com sucesso!", "success")
        else:
            self._log("Aviso: Não foi possível configurar permissões automaticamente", "warning")
            self._log("Execute: xhost +SI:localuser:root", "warning")


class UninstallThread(QThread):
    """Thread para desinstalação"""
    
    log = pyqtSignal(str, str)
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)
    step = pyqtSignal(int)
    
    def run(self):
        try:
            self._uninstall()
        except Exception as e:
            self.log.emit(f"Erro: {str(e)}", "error")
            self.finished.emit(False, str(e))
    
    def _uninstall(self):
        self.log.emit("=" * 40, "info")
        self.log.emit("INICIANDO DESINSTALAÇÃO", "info")
        self.log.emit("=" * 40, "info")
        
        self.progress.emit("Removendo arquivos...", 20)
        self.log.emit(f"Removendo: {INSTALL_DIR}", "detail")
        
        if INSTALL_DIR.exists():
            shutil.rmtree(INSTALL_DIR)
        
        self.step.emit(30)
        
        self.progress.emit("Removendo lançador...", 50)
        self.log.emit(f"Removendo: {DESKTOP_FILE}", "detail")
        if DESKTOP_FILE.exists():
            DESKTOP_FILE.unlink()
        
        self.step.emit(50)
        
        self.progress.emit("Removendo autostart...", 70)
        self.log.emit(f"Removendo: {AUTOSTART_FILE}", "detail")
        if AUTOSTART_FILE.exists():
            AUTOSTART_FILE.unlink()
        
        self.step.emit(70)
        
        self.progress.emit("Limpando configurações...", 90)
        config_dir = Path.home() / ".config" / "amarelo-keys"
        if config_dir.exists():
            self.log.emit(f"Removendo: {config_dir}", "detail")
            shutil.rmtree(config_dir)
        
        self.step.emit(100)
        self.progress.emit("Desinstalação concluída!", 100)
        self.log.emit("=" * 40, "success")
        self.log.emit("DESINSTALAÇÃO CONCLUÍDA!", "success")
        self.log.emit("=" * 40, "success")
        self.finished.emit(True, "Desinstalação realizada com sucesso!")


class GradientFrame(QFrame):
    """Frame com gradiente"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#1a2332"))
        gradient.setColorAt(1, QColor("#0f1621"))
        
        painter.fillRect(self.rect(), gradient)


class StatusIndicator(QWidget):
    """Indicador de status visual"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = "pending"
        self.setFixedSize(12, 12)
        
    def setStatus(self, status):
        self.status = status
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.status == "success":
            color = QColor("#4ecdc4")
        elif self.status == "error":
            color = QColor("#ff6b6b")
        elif self.status == "running":
            color = QColor("#FFD700")
        else:
            color = QColor("#666666")
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 10, 10)


class InstallerWindow(QMainWindow):
    """Janela principal do instalador"""
    
    def __init__(self):
        super().__init__()
        self.is_installed = self._check_installed()
        self._setup_ui()
        self._setup_styles()
        
    def _check_installed(self):
        return INSTALL_DIR.exists() and (INSTALL_DIR / "amarelo_keys.py").exists()
    
    def _setup_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1621;
            }
            QWidget {
                background-color: #0f1621;
                color: #e0e0e0;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2d3a4f;
                color: #FFD700;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3d4a5f;
            }
            QPushButton:pressed {
                background-color: #1d2a3f;
            }
            QPushButton:disabled {
                background-color: #1e2a3a;
                color: #555;
            }
            QPushButton#primary {
                background-color: #FFD700;
                color: #1a1a2e;
            }
            QPushButton#primary:hover {
                background-color: #FFC000;
            }
            QPushButton#danger {
                background-color: #ff6b6b;
                color: #fff;
            }
            QPushButton#danger:hover {
                background-color: #ff5252;
            }
            QTextEdit {
                background-color: #151d28;
                border: 1px solid #2a3545;
                border-radius: 8px;
                color: #aaa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 8px;
            }
            QProgressBar {
                background-color: #151d28;
                border: 2px solid #2a3545;
                border-radius: 8px;
                text-align: center;
                color: #FFD700;
                font-weight: bold;
                height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #FFD700, stop:1 #FFC000);
                border-radius: 6px;
            }
            QCheckBox {
                color: #e0e0e0;
                spacing: 10px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #FFD700;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #FFD700;
                image: none;
            }
            QCheckBox::indicator:hover {
                background-color: rgba(255, 215, 0, 0.2);
            }
            QGroupBox {
                border: 1px solid #2a3545;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 20px;
                padding-bottom: 12px;
                font-weight: bold;
                color: #888;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                padding: 0 8px;
                color: #FFD700;
            }
            QScrollBar:vertical {
                background-color: #151d28;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d4a5c;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4d5a6c;
            }
            QMessageBox {
                background-color: #1a2332;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                min-width: 100px;
            }
        """)
    
    def _setup_ui(self):
        self.setWindowTitle(f"Instalador - {APP_NAME} v{VERSION}")
        self.setMinimumSize(650, 550)
        self.resize(700, 600)
        self.setWindowIcon(self._create_icon())
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        header_frame = GradientFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 20, 24, 16)
        header_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel(f"⚙  {APP_NAME}")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #FFD700;
        """)
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        subtitle = QLabel(f"Instalador v{VERSION}  •  Acessibilidade para Linux")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #888;
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)
        
        main_layout.addWidget(header_frame)
        
        content = QWidget()
        content.setStyleSheet("background-color: #0f1621;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)
        
        if self.is_installed:
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(0, 0, 0, 0)
            
            status_indicator = StatusIndicator()
            status_indicator.setStatus("success")
            status_layout.addWidget(status_indicator)
            
            status_text = QLabel("✓ O Amarelo Keys já está instalado")
            status_text.setStyleSheet("color: #4ecdc4; font-weight: bold; font-size: 14px;")
            status_layout.addWidget(status_text)
            status_layout.addStretch()
            
            content_layout.addWidget(status_widget)
        
        options_group = QGroupBox("Opções de Instalação")
        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)
        
        self.deps_cb = QCheckBox("Instalar dependências (PyQt5, python-xlib)")
        self.deps_cb.setChecked(True)
        self.deps_cb.setToolTip("Baixa e instala os pacotes necessários")
        options_layout.addWidget(self.deps_cb)
        
        self.launcher_cb = QCheckBox("Criar lançador no menu de aplicativos")
        self.launcher_cb.setChecked(True)
        self.launcher_cb.setToolTip("Adiciona o aplicativo ao menu do sistema")
        options_layout.addWidget(self.launcher_cb)
        
        self.autostart_cb = QCheckBox("Iniciar automaticamente com o sistema")
        self.autostart_cb.setChecked(True)
        self.autostart_cb.setToolTip("Inicia o aplicativo automaticamente ao fazer login")
        options_layout.addWidget(self.autostart_cb)
        
        self.perms_cb = QCheckBox("Configurar permissões de teclado (xhost)")
        self.perms_cb.setChecked(True)
        self.perms_cb.setToolTip("Permite que o app capture teclas globais")
        options_layout.addWidget(self.perms_cb)
        
        options_group.setLayout(options_layout)
        content_layout.addWidget(options_group)
        
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #4ecdc4; font-weight: bold; font-size: 13px;")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(140)
        self.log_text.setVisible(False)
        progress_layout.addWidget(self.log_text)
        
        content_layout.addWidget(progress_widget)
        
        content_layout.addStretch()
        
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(12)
        
        buttons_layout.addStretch()
        
        self.install_btn = QPushButton("▶  Instalar")
        self.install_btn.setObjectName("primary")
        self.install_btn.setMinimumWidth(140)
        self.install_btn.clicked.connect(self._start_install)
        buttons_layout.addWidget(self.install_btn)
        
        self.uninstall_btn = QPushButton("✖  Desinstalar")
        self.uninstall_btn.setObjectName("danger")
        self.uninstall_btn.setMinimumWidth(140)
        self.uninstall_btn.clicked.connect(self._start_uninstall)
        buttons_layout.addWidget(self.uninstall_btn)
        
        self.close_btn = QPushButton("Fechar")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)
        
        buttons_layout.addStretch()
        
        content_layout.addWidget(buttons_widget)
        
        footer = QLabel(f"© 2025 {AUTHOR}  •  MIT License")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #555; font-size: 11px; padding-bottom: 8px;")
        content_layout.addWidget(footer)
        
        main_layout.addWidget(content)
    
    def _create_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(QBrush(QColor("#FFD700")))
        painter.setPen(QPen(QColor("#B8860B"), 3))
        painter.drawEllipse(8, 8, 48, 48)
        
        painter.setPen(QPen(QColor("#1a1a2e"), 4))
        painter.drawLine(24, 18, 24, 32)
        painter.drawLine(24, 38, 24, 46)
        
        painter.end()
        return QIcon(pixmap)
    
    def _set_buttons_enabled(self, enabled):
        self.install_btn.setEnabled(enabled)
        self.uninstall_btn.setEnabled(enabled)
        self.close_btn.setEnabled(enabled)
        self.deps_cb.setEnabled(enabled)
        self.launcher_cb.setEnabled(enabled)
        self.autostart_cb.setEnabled(enabled)
        self.perms_cb.setEnabled(enabled)
    
    def _start_install(self):
        options = {
            'install_deps': self.deps_cb.isChecked(),
            'create_launcher': self.launcher_cb.isChecked(),
            'autostart': self.autostart_cb.isChecked(),
            'setup_permissions': self.perms_cb.isChecked(),
        }
        
        self._set_buttons_enabled(False)
        self.progress_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.log_text.setVisible(True)
        self.progress_label.setText("Preparando instalação...")
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        self.thread = InstallerThread(options)
        self.thread.log.connect(self._on_log)
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.step.connect(self._on_step)
        self.thread.start()
    
    def _start_uninstall(self):
        reply = QMessageBox.question(
            self, "Confirmar Desinstalação",
            f" Deseja realmente desinstalar o {APP_NAME}?\n\n"
            "Isso removerá:\n"
            "  • Arquivos do aplicativo\n"
            "  • Lançador do menu\n"
            "  • Configurações de autostart\n"
            "  • Todas as configurações salvas",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self._set_buttons_enabled(False)
        self.progress_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.log_text.setVisible(True)
        self.progress_label.setText("Preparando desinstalação...")
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        self.thread = UninstallThread()
        self.thread.log.connect(self._on_log)
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.step.connect(self._on_step)
        self.thread.start()
    
    def _on_log(self, msg, level):
        self.log_text.append(msg)
        self.log_text.ensureCursorVisible()
    
    def _on_progress(self, msg, val):
        self.progress_label.setText(msg)
        if val >= 0:
            self.progress_bar.setValue(val)
    
    def _on_step(self, val):
        self.progress_bar.setValue(val)
    
    def _on_finished(self, success, msg):
        self._set_buttons_enabled(True)
        
        if success:
            self.progress_label.setText("✓ Concluído!")
            
            if "INSTALAÇÃO" in self.log_text.toPlainText():
                QMessageBox.information(
                    self, "Sucesso",
                    f"{APP_NAME} foi instalado com sucesso!\n\n"
                    "Você pode iniciá-lo pelo menu de aplicativos\n"
                    "ou executando: python3 ~/.local/share/amarelo-keys/amarelo_keys.py"
                )
            else:
                QMessageBox.information(
                    self, "Sucesso",
                    msg
                )
            
            self.is_installed = self._check_installed()
        else:
            self.progress_label.setText("✗ Erro")
            QMessageBox.critical(
                self, "Erro",
                f"Falha na operação:\n\n{msg}"
            )
    
    def closeEvent(self, event):
        if hasattr(self, 'thread') and self.thread.isRunning():
            reply = QMessageBox.question(
                self, "Confirmar",
                "Instalação em andamento. Deseja realmente sair?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(f"Instalador - {APP_NAME}")
    app.setApplicationVersion(VERSION)
    app.setQuitOnLastWindowClosed(True)
    
    window = InstallerWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
