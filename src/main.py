import sys
import os
import subprocess
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox, QFileDialog, QMessageBox,
    QGroupBox, QFrame, QProgressBar, QSizePolicy, QTabWidget, QComboBox,
    QSpinBox, QListWidget, QListWidgetItem, QAbstractItemView, QSplitter, QToolButton
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QTextCursor, QPalette, QColor

# Set log format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


class PackageThread(QThread):
    """Thread for executing packaging commands"""
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(bool)

    def __init__(self, command, parent=None):
        super().__init__(parent)
        self.command = command
        self.running = True
        self.process = None  # Reference to subprocess
        

    def run(self):
        """Execute packaging command and capture output"""
        self.log_signal.emit(f"Starting packaging command: {' '.join(self.command)}\n")
        try:
            # Create subprocess to execute command
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            # Read output in real-time
            for line in iter(self.process.stdout.readline, ''):
                if not self.running:
                    break
                self.log_signal.emit(line.strip())

            # Wait for process to finish
            return_code = self.process.wait()
            if return_code == 0:
                self.log_signal.emit("\n✅ Packaging completed successfully!")
                self.finished_signal.emit(True)
            else:
                self.log_signal.emit(f"\n❌ Packaging failed with error code: {return_code}")
                self.finished_signal.emit(False)
        except Exception as e:
            self.log_signal.emit(f"\n❌ Error during execution: {str(e)}")
            self.finished_signal.emit(False)

    def stop(self):
        """Stop packaging process"""
        self.running = False
        self.log_signal.emit("\n🛑 User requested packaging stop...")

        # Attempt to terminate subprocess
        if self.process:
            try:
                self.process.terminate()
            except Exception as e:
                self.log_signal.emit(f"⚠️ Failed to terminate process: {str(e)}")


class NuitkaPackager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nuitka Advanced Packager")
        self.setGeometry(100, 100, 1000, 850)

        # Set window icon
        self.setWindowIcon(QIcon("../icons/382_128x128.ico"))  # Replace with your icon path


        # Apply stylesheet directly on QMainWindow
        


        # Initialize UI
        self.init_ui()

        # Initial state
        self.python_path = ""
        self.main_file = ""
        self.icon_file = ""
        self.output_dir = ""
        self.package_thread = None
        self.plugins = []
        
        self.is_dark_theme = False  # Default to light theme


        # Apply styling
        self.set_style()
        '''self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0d0d0f,
                    stop: 0.4 #1a1a1f,
                    stop: 0.7 #0f1f2f,
                    stop: 1 #0d0d0f
                );
            }
        """)'''
        # Update command display
        self.update_command()

    def init_ui(self):
        """Initialize user interface"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Nuitka Advanced Packager")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        main_layout.addWidget(title_label)

        # Use tabs to organize the interface
        main_tab = QTabWidget()
        main_layout.addWidget(main_tab)

        # ===== File Configuration Tab =====
        file_config_tab = QWidget()
        file_config_layout = QVBoxLayout(file_config_tab)
        file_config_layout.setContentsMargins(10, 10, 10, 10)
        file_config_layout.setSpacing(15)

        # File configuration area
        config_group = QGroupBox("File Path Configuration")
        config_layout = QGridLayout(config_group)
        config_layout.setSpacing(10)
        config_layout.setContentsMargins(15, 15, 15, 15)

        # Python interpreter selection
        self.python_label = QLabel("Python Interpreter:")
        self.python_input = QLineEdit()
        self.python_input.setPlaceholderText("Select Python interpreter (e.g., venv/Scripts/python.exe)")
        self.python_btn = QPushButton("Browse...")
        self.python_btn.clicked.connect(self.select_python)

        # Main file selection
        self.file_label = QLabel("Main File:")
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Select main Python file to package")
        self.file_btn = QPushButton("Browse...")
        self.file_btn.clicked.connect(self.select_main_file)

        # Icon file selection
        self.icon_label = QLabel("Icon File:")
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("Optional - Select program icon (.ico)")
        self.icon_btn = QPushButton("Browse...")
        self.icon_btn.clicked.connect(self.select_icon)

        # Output directory selection
        self.output_label = QLabel("Output Directory:")
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Select output directory for packaged files")
        self.output_btn = QPushButton("Browse...")
        self.output_btn.clicked.connect(self.select_output_dir)

        # Add configuration items to layout
        config_layout.addWidget(self.python_label, 0, 0)
        config_layout.addWidget(self.python_input, 0, 1)
        config_layout.addWidget(self.python_btn, 0, 2)

        config_layout.addWidget(self.file_label, 1, 0)
        config_layout.addWidget(self.file_input, 1, 1)
        config_layout.addWidget(self.file_btn, 1, 2)

        config_layout.addWidget(self.icon_label, 2, 0)
        config_layout.addWidget(self.icon_input, 2, 1)
        config_layout.addWidget(self.icon_btn, 2, 2)

        config_layout.addWidget(self.output_label, 3, 0)
        config_layout.addWidget(self.output_input, 3, 1)
        config_layout.addWidget(self.output_btn, 3, 2)

        file_config_layout.addWidget(config_group)
        file_config_layout.addStretch()

        # Add file config tab to main tabs
        main_tab.addTab(file_config_tab, "File Configuration")

        # ===== Common Options Tab =====
        common_tab = QWidget()
        common_layout = QVBoxLayout(common_tab)
        common_layout.setContentsMargins(10, 10, 10, 10)
        common_layout.setSpacing(15)

        # Common options group
        common_group = QGroupBox("Common Packaging Options")
        common_group_layout = QGridLayout(common_group)
        common_group_layout.setSpacing(10)

        # Common options
        self.onefile_check = QCheckBox("--onefile (Single executable file)")
        self.onefile_check.setChecked(False)
        self.onefile_check.stateChanged.connect(self.update_command)

        self.standalone_check = QCheckBox("--standalone (Standalone mode with all dependencies)")
        self.standalone_check.setChecked(True)
        self.standalone_check.stateChanged.connect(self.update_command)

        self.disable_console_check = QCheckBox("--windows-disable-console (Hide console window)")
        self.disable_console_check.setChecked(True)
        self.disable_console_check.stateChanged.connect(self.update_command)

        self.remove_output_check = QCheckBox("--remove-output (Clean up after packaging)")
        self.remove_output_check.setChecked(True)
        self.remove_output_check.stateChanged.connect(self.update_command)

        self.include_qt_check = QCheckBox("--include-qt (Include Qt plugins for PySide6/PyQt6)")
        self.include_qt_check.setChecked(False)
        self.include_qt_check.stateChanged.connect(self.update_command)

        self.show_progress_check = QCheckBox("--show-progress (Show packaging progress)")
        self.show_progress_check.setChecked(True)
        self.show_progress_check.stateChanged.connect(self.update_command)

        self.show_memory_check = QCheckBox("--show-memory (Show memory usage)")
        self.show_memory_check.setChecked(False)
        self.show_memory_check.stateChanged.connect(self.update_command)

        # Add common options to layout
        common_group_layout.addWidget(self.onefile_check, 0, 0)
        common_group_layout.addWidget(self.standalone_check, 0, 1)
        common_group_layout.addWidget(self.disable_console_check, 0, 2)

        common_group_layout.addWidget(self.remove_output_check, 1, 0)
        common_group_layout.addWidget(self.include_qt_check, 1, 1)
        common_group_layout.addWidget(self.show_progress_check, 1, 2)

        common_group_layout.addWidget(self.show_memory_check, 2, 0)

        common_layout.addWidget(common_group)
        common_layout.addStretch()

        # Add common options tab to main tabs
        main_tab.addTab(common_tab, "Common Options")

        # ===== Plugin Options Tab =====
        plugins_tab = QWidget()
        plugins_layout = QVBoxLayout(plugins_tab)
        plugins_layout.setContentsMargins(10, 10, 10, 10)
        plugins_layout.setSpacing(15)

        # Plugin options group
        plugins_group = QGroupBox("Plugin Options")
        plugins_group_layout = QVBoxLayout(plugins_group)

        # Plugin information
        plugins_info = QLabel("Select Nuitka plugins to enable. Common plugins:\n"
                              "- pyside6: Support for PySide6 framework\n"
                              "- tk-inter: Support for Tkinter GUI library\n"
                              "- numpy: Support for NumPy scientific library\n"
                              "- multiprocessing: Support for multiprocessing module")
        plugins_info.setWordWrap(True)
        plugins_info.setStyleSheet("background-color: #f8f9fa; padding: 8px; border-radius: 4px;")
        plugins_group_layout.addWidget(plugins_info)

        self.plugins_list = QListWidget()
        self.plugins_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.plugins_list.setMinimumHeight(250)

        # Add common plugins
        common_plugins = [
            "pyside6", "tk-inter", "numpy", "multiprocessing",
            "dill-compat", "gevent", "pylint-warnings", "qt-plugins",
            "anti-bloat", "playwright", "spacy", "pandas"
        ]
        for plugin in common_plugins:
            item = QListWidgetItem(f"--enable-plugin={plugin}")
            self.plugins_list.addItem(item)

        plugins_group_layout.addWidget(self.plugins_list)
        self.plugins_list.itemSelectionChanged.connect(self.update_command)

        plugins_layout.addWidget(plugins_group)
        plugins_layout.addStretch()

        # Add plugin options tab to main tabs
        main_tab.addTab(plugins_tab, "Plugin Options")

        # ===== Python Flags Tab =====
        flags_tab = QWidget()
        flags_layout = QVBoxLayout(flags_tab)
        flags_layout.setContentsMargins(10, 10, 10, 10)
        flags_layout.setSpacing(15)

        # Python flags group
        flags_group = QGroupBox("Python Flags")
        flags_group_layout = QVBoxLayout(flags_group)
        flags_group_layout.setSpacing(10)

        # Flags information
        flags_info = QLabel("Python flags set runtime options for the interpreter:\n"
                            "- no_site: Disable site module import\n"
                            "- no_warnings: Suppress warning messages\n"
                            "- no_asserts: Disable assert statements\n"
                            "- no_docstrings: Remove docstrings\n"
                            "- unbuffered: Unbuffered output\n"
                            "- static_hashes: Use static hash values")
        flags_info.setWordWrap(True)
        flags_info.setStyleSheet("background-color: #f8f9fa; padding: 8px; border-radius: 4px;")
        flags_group_layout.addWidget(flags_info)

        # Flag selector and buttons
        flags_selector_layout = QHBoxLayout()

        self.flags_combo = QComboBox()
        self.flags_combo.addItems([
            "--python-flag=no_site",
            "--python-flag=no_warnings",
            "--python-flag=no_asserts",
            "--python-flag=no_docstrings",
            "--python-flag=unbuffered",
            "--python-flag=static_hashes"
        ])
        self.flags_combo.setCurrentIndex(-1)
        self.flags_combo.setMinimumWidth(250)

        self.add_flag_btn = QPushButton("Add Flag")
        self.add_flag_btn.clicked.connect(self.add_python_flag)
        self.add_flag_btn.setFixedWidth(100)

        self.remove_flag_btn = QPushButton("Remove Flag")
        self.remove_flag_btn.clicked.connect(self.remove_python_flag)
        self.remove_flag_btn.setFixedWidth(100)
        self.remove_flag_btn.setEnabled(False)

        flags_selector_layout.addWidget(self.flags_combo)
        flags_selector_layout.addWidget(self.add_flag_btn)
        flags_selector_layout.addWidget(self.remove_flag_btn)
        flags_selector_layout.addStretch()

        flags_group_layout.addLayout(flags_selector_layout)

        # Selected flags list
        self.flags_list = QListWidget()
        self.flags_list.setMinimumHeight(120)
        self.flags_list.itemSelectionChanged.connect(self.toggle_remove_button)
        flags_group_layout.addWidget(self.flags_list)

        flags_layout.addWidget(flags_group)
        flags_layout.addStretch()

        # Add Python flags tab to main tabs
        main_tab.addTab(flags_tab, "Python Flags")

        # ===== Advanced Options Tab =====
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setContentsMargins(10, 10, 10, 10)
        advanced_layout.setSpacing(15)

        # Advanced options group
        advanced_group = QGroupBox("Advanced Packaging Options")
        advanced_group_layout = QGridLayout(advanced_group)
        advanced_group_layout.setSpacing(10)

        # Advanced options
        self.follow_imports_check = QCheckBox("--follow-imports (Include all imported modules)")
        self.follow_imports_check.setChecked(True)
        self.follow_imports_check.stateChanged.connect(self.update_command)

        self.follow_stdlib_check = QCheckBox("--follow-stdlib (Include standard library modules)")
        self.follow_stdlib_check.setChecked(False)
        self.follow_stdlib_check.stateChanged.connect(self.update_command)

        self.module_mode_check = QCheckBox("--module (Create importable binary extension)")
        self.module_mode_check.setChecked(False)
        self.module_mode_check.stateChanged.connect(self.update_command)

        self.lto_check = QCheckBox("--lto (Enable link-time optimization)")
        self.lto_check.setChecked(False)
        self.lto_check.stateChanged.connect(self.update_command)

        self.disable_ccache_check = QCheckBox("--disable-ccache (Disable ccache)")
        self.disable_ccache_check.setChecked(False)
        self.disable_ccache_check.stateChanged.connect(self.update_command)

        self.assume_yes_check = QCheckBox("--assume-yes (Answer yes to all prompts)")
        self.assume_yes_check.setChecked(False)
        self.assume_yes_check.stateChanged.connect(self.update_command)

        self.windows_uac_admin_check = QCheckBox("--windows-uac-admin (Request admin privileges)")
        self.windows_uac_admin_check.setChecked(False)
        self.windows_uac_admin_check.stateChanged.connect(self.update_command)

        self.windows_uac_uiaccess_check = QCheckBox("--windows-uac-uiaccess (Allow elevated UI interaction)")
        self.windows_uac_uiaccess_check.setChecked(False)
        self.windows_uac_uiaccess_check.stateChanged.connect(self.update_command)

        # Add advanced options to layout
        advanced_group_layout.addWidget(self.follow_imports_check, 0, 0)
        advanced_group_layout.addWidget(self.follow_stdlib_check, 0, 1)
        advanced_group_layout.addWidget(self.module_mode_check, 0, 2)

        advanced_group_layout.addWidget(self.lto_check, 1, 0)
        advanced_group_layout.addWidget(self.disable_ccache_check, 1, 1)
        advanced_group_layout.addWidget(self.assume_yes_check, 1, 2)

        advanced_group_layout.addWidget(self.windows_uac_admin_check, 2, 0)
        advanced_group_layout.addWidget(self.windows_uac_uiaccess_check, 2, 1)

        advanced_layout.addWidget(advanced_group)

        # Include options group
        include_group = QGroupBox("Include Options")
        include_layout = QGridLayout(include_group)
        include_layout.setSpacing(10)

        # Include package
        self.include_package_label = QLabel("Include Package:")
        self.include_package_input = QLineEdit()
        self.include_package_input.setPlaceholderText("Package name (e.g., mypackage)")
        self.include_package_input.textChanged.connect(self.update_command)

        # Include package data
        self.include_package_data_label = QLabel("Include Package Data:")
        self.include_package_data_input = QLineEdit()
        self.include_package_data_input.setPlaceholderText("Package:pattern (e.g., mypackage:*.txt)")
        self.include_package_data_input.textChanged.connect(self.update_command)

        # Include module
        self.include_module_label = QLabel("Include Module:")
        self.include_module_input = QLineEdit()
        self.include_module_input.setPlaceholderText("Module name (e.g., mymodule)")
        self.include_module_input.textChanged.connect(self.update_command)

        # Include data files
        self.include_data_label = QLabel("Include Data Files:")
        self.include_data_input = QLineEdit()
        self.include_data_input.setPlaceholderText("Source=Destination (e.g., data/*.json=./data/)")
        self.include_data_input.textChanged.connect(self.update_command)

        # Include data directory
        self.include_data_dir_label = QLabel("Include Data Directory:")
        self.include_data_dir_input = QLineEdit()
        self.include_data_dir_input.setPlaceholderText("Source=Destination (e.g., ./assets=assets/)")
        self.include_data_dir_input.textChanged.connect(self.update_command)

        # Exclude data files
        self.noinclude_data_label = QLabel("Exclude Data Files:")
        self.noinclude_data_input = QLineEdit()
        self.noinclude_data_input.setPlaceholderText("Pattern (e.g., *.tmp)")
        self.noinclude_data_input.textChanged.connect(self.update_command)

        # Onefile external data
        self.include_onefile_ext_label = QLabel("Onefile External Data:")
        self.include_onefile_ext_input = QLineEdit()
        self.include_onefile_ext_input.setPlaceholderText("Pattern (e.g., large_files/*)")
        self.include_onefile_ext_input.textChanged.connect(self.update_command)

        # Include raw directory
        self.include_raw_dir_label = QLabel("Include Raw Directory:")
        self.include_raw_dir_input = QLineEdit()
        self.include_raw_dir_input.setPlaceholderText("Directory path (e.g., ./raw_data)")
        self.include_raw_dir_input.textChanged.connect(self.update_command)

        # Add include options to layout
        include_layout.addWidget(self.include_package_label, 0, 0)
        include_layout.addWidget(self.include_package_input, 0, 1)

        include_layout.addWidget(self.include_package_data_label, 1, 0)
        include_layout.addWidget(self.include_package_data_input, 1, 1)

        include_layout.addWidget(self.include_module_label, 2, 0)
        include_layout.addWidget(self.include_module_input, 2, 1)

        include_layout.addWidget(self.include_data_label, 3, 0)
        include_layout.addWidget(self.include_data_input, 3, 1)

        include_layout.addWidget(self.include_data_dir_label, 4, 0)
        include_layout.addWidget(self.include_data_dir_input, 4, 1)

        include_layout.addWidget(self.noinclude_data_label, 5, 0)
        include_layout.addWidget(self.noinclude_data_input, 5, 1)

        include_layout.addWidget(self.include_onefile_ext_label, 6, 0)
        include_layout.addWidget(self.include_onefile_ext_input, 6, 1)

        include_layout.addWidget(self.include_raw_dir_label, 7, 0)
        include_layout.addWidget(self.include_raw_dir_input, 7, 1)

        advanced_layout.addWidget(include_group)
        advanced_layout.addStretch()

        # Add advanced options tab to main tabs
        main_tab.addTab(advanced_tab, "Advanced Options")

        # ===== Onefile Options Tab =====
        onefile_tab = QWidget()
        onefile_layout = QVBoxLayout(onefile_tab)
        onefile_layout.setContentsMargins(10, 10, 10, 10)
        onefile_layout.setSpacing(15)

        # Onefile options group
        onefile_group = QGroupBox("Onefile Mode Options")
        onefile_group_layout = QGridLayout(onefile_group)
        onefile_group_layout.setSpacing(10)

        # Onefile options
        self.onefile_tempdir_label = QLabel("Temp Directory:")
        self.onefile_tempdir_input = QLineEdit()
        self.onefile_tempdir_input.setPlaceholderText("{TEMP}/onefile_{PID}_{TIME} (default)")
        self.onefile_tempdir_input.textChanged.connect(self.update_command)

        self.onefile_grace_time_label = QLabel("Child Termination Time (ms):")
        self.onefile_grace_time_spin = QSpinBox()
        self.onefile_grace_time_spin.setRange(1000, 30000)
        self.onefile_grace_time_spin.setValue(5000)
        self.onefile_grace_time_spin.valueChanged.connect(self.update_command)

        self.onefile_no_compression_check = QCheckBox("--onefile-no-compression (Disable compression)")
        self.onefile_no_compression_check.setChecked(False)
        self.onefile_no_compression_check.stateChanged.connect(self.update_command)

        self.onefile_as_archive_check = QCheckBox("--onefile-as-archive (Create extractable archive)")
        self.onefile_as_archive_check.setChecked(False)
        self.onefile_as_archive_check.stateChanged.connect(self.update_command)

        # Add onefile options to layout
        onefile_group_layout.addWidget(self.onefile_tempdir_label, 0, 0)
        onefile_group_layout.addWidget(self.onefile_tempdir_input, 0, 1)

        onefile_group_layout.addWidget(self.onefile_grace_time_label, 1, 0)
        onefile_group_layout.addWidget(self.onefile_grace_time_spin, 1, 1)

        onefile_group_layout.addWidget(self.onefile_no_compression_check, 2, 0)
        onefile_group_layout.addWidget(self.onefile_as_archive_check, 2, 1)

        onefile_layout.addWidget(onefile_group)

        # DLL control group
        dll_group = QGroupBox("DLL Control")
        dll_layout = QGridLayout(dll_group)

        # DLL options
        self.noinclude_dlls_label = QLabel("Exclude DLLs:")
        self.noinclude_dlls_input = QLineEdit()
        self.noinclude_dlls_input.setPlaceholderText("Pattern (e.g., someDLL.*)")
        self.noinclude_dlls_input.textChanged.connect(self.update_command)

        # Add DLL options to layout
        dll_layout.addWidget(self.noinclude_dlls_label, 0, 0)
        dll_layout.addWidget(self.noinclude_dlls_input, 0, 1)

        onefile_layout.addWidget(dll_group)
        onefile_layout.addStretch()

        # Add onefile options tab to main tabs
        main_tab.addTab(onefile_tab, "Onefile Options")

        # ===== Metadata Tab =====
        metadata_tab = QWidget()
        metadata_layout = QVBoxLayout(metadata_tab)
        metadata_layout.setContentsMargins(10, 10, 10, 10)
        metadata_layout.setSpacing(15)

        # Metadata group
        metadata_group = QGroupBox("Metadata Information")
        metadata_group_layout = QGridLayout(metadata_group)
        metadata_group_layout.setSpacing(10)

        # Metadata options
        self.company_label = QLabel("Company Name:")
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Optional - Company name")
        self.company_input.textChanged.connect(self.update_command)

        self.product_label = QLabel("Product Name:")
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("Optional - Product name")
        self.product_input.textChanged.connect(self.update_command)

        self.file_version_label = QLabel("File Version:")
        self.file_version_input = QLineEdit()
        self.file_version_input.setPlaceholderText("Format: X.Y.Z.W")
        self.file_version_input.textChanged.connect(self.update_command)

        self.product_version_label = QLabel("Product Version:")
        self.product_version_input = QLineEdit()
        self.product_version_input.setPlaceholderText("Format: X.Y.Z.W")
        self.product_version_input.textChanged.connect(self.update_command)

        self.file_description_label = QLabel("File Description:")
        self.file_description_input = QLineEdit()
        self.file_description_input.setPlaceholderText("Optional - File description")
        self.file_description_input.textChanged.connect(self.update_command)

        self.copyright_label = QLabel("Copyright:")
        self.copyright_input = QLineEdit()
        self.copyright_input.setPlaceholderText("Optional - Copyright information")
        self.copyright_input.textChanged.connect(self.update_command)

        # Add metadata options to layout
        metadata_group_layout.addWidget(self.company_label, 0, 0)
        metadata_group_layout.addWidget(self.company_input, 0, 1)

        metadata_group_layout.addWidget(self.product_label, 1, 0)
        metadata_group_layout.addWidget(self.product_input, 1, 1)

        metadata_group_layout.addWidget(self.file_version_label, 2, 0)
        metadata_group_layout.addWidget(self.file_version_input, 2, 1)

        metadata_group_layout.addWidget(self.product_version_label, 3, 0)
        metadata_group_layout.addWidget(self.product_version_input, 3, 1)

        metadata_group_layout.addWidget(self.file_description_label, 4, 0)
        metadata_group_layout.addWidget(self.file_description_input, 4, 1)

        metadata_group_layout.addWidget(self.copyright_label, 5, 0)
        metadata_group_layout.addWidget(self.copyright_input, 5, 1)

        metadata_layout.addWidget(metadata_group)

        # Environment control group
        env_group = QGroupBox("Environment Control")
        env_layout = QGridLayout(env_group)

        # Environment options
        self.force_env_label = QLabel("Force Environment Variable:")
        self.force_env_input = QLineEdit()
        self.force_env_input.setPlaceholderText("VAR=value (e.g., MY_VAR=123)")
        self.force_env_input.textChanged.connect(self.update_command)

        # Add environment options to layout
        env_layout.addWidget(self.force_env_label, 0, 0)
        env_layout.addWidget(self.force_env_input, 0, 1)

        metadata_layout.addWidget(env_group)
        metadata_layout.addStretch()

        # Add metadata tab to main tabs
        main_tab.addTab(metadata_tab, "Metadata")

        # ===== Debug Options Tab =====
        debug_tab = QWidget()
        debug_layout = QVBoxLayout(debug_tab)
        debug_layout.setContentsMargins(10, 10, 10, 10)
        debug_layout.setSpacing(15)

        # Debug options group
        debug_group = QGroupBox("Debug Options")
        debug_group_layout = QGridLayout(debug_group)
        debug_group_layout.setSpacing(10)

        # Debug options
        self.debug_check = QCheckBox("--debug (Enable debug mode)")
        self.debug_check.setChecked(False)
        self.debug_check.stateChanged.connect(self.update_command)

        self.unstripped_check = QCheckBox("--unstripped (Keep debug information)")
        self.unstripped_check.setChecked(False)
        self.unstripped_check.stateChanged.connect(self.update_command)

        self.trace_execution_check = QCheckBox("--trace-execution (Trace execution)")
        self.trace_execution_check.setChecked(False)
        self.trace_execution_check.stateChanged.connect(self.update_command)

        self.warn_implicit_check = QCheckBox("--warn-implicit-exceptions (Warn on implicit exceptions)")
        self.warn_implicit_check.setChecked(False)
        self.warn_implicit_check.stateChanged.connect(self.update_command)

        self.warn_unusual_check = QCheckBox("--warn-unusual-code (Warn on unusual code)")
        self.warn_unusual_check.setChecked(False)
        self.warn_unusual_check.stateChanged.connect(self.update_command)

        # Add debug options to layout
        debug_group_layout.addWidget(self.debug_check, 0, 0)
        debug_group_layout.addWidget(self.unstripped_check, 0, 1)

        debug_group_layout.addWidget(self.trace_execution_check, 1, 0)
        debug_group_layout.addWidget(self.warn_implicit_check, 1, 1)

        debug_group_layout.addWidget(self.warn_unusual_check, 2, 0)

        debug_layout.addWidget(debug_group)

        # Deployment control group
        deployment_group = QGroupBox("Deployment Control")
        deployment_layout = QGridLayout(deployment_group)

        # Deployment options
        self.deployment_check = QCheckBox("--deployment (Enable deployment mode)")
        self.deployment_check.setChecked(False)
        self.deployment_check.stateChanged.connect(self.update_command)

        # Add deployment options to layout
        deployment_layout.addWidget(self.deployment_check, 0, 0)

        debug_layout.addWidget(deployment_group)
        debug_layout.addStretch()

        # Add debug options tab to main tabs
        main_tab.addTab(debug_tab, "Debug Options")

        # ===== Operation Log Tab =====
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(15)

        # Log area
        log_group = QGroupBox("Operation Log")
        log_group_layout = QVBoxLayout(log_group)
        log_group_layout.setContentsMargins(15, 15, 15, 15)
        log_group.setMinimumHeight(450)  # Fixed minimum height

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(QFont("Consolas", 9))
        log_group_layout.addWidget(self.log_edit)

        # Add log box to layout
        log_layout.addWidget(log_group)
        log_layout.addStretch()

        # Add log tab to main tabs
        main_tab.addTab(log_tab, "Operation Log")

        # Command area
        command_group = QGroupBox("Packaging Command")
        command_layout = QVBoxLayout(command_group)
        command_layout.setContentsMargins(15, 15, 15, 15)
        command_group.setMinimumHeight(150)  # Fixed minimum height

        self.command_edit = QTextEdit()
        self.command_edit.setPlaceholderText("Generated packaging command will appear here...")
        self.command_edit.setFont(QFont("Consolas", 10))
        self.command_edit.setMinimumHeight(80)
        command_layout.addWidget(self.command_edit)

        main_layout.addWidget(command_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        main_layout.addWidget(self.progress_bar)

        # Theme toggle button
        theme_layout = QHBoxLayout()
        self.theme_toggle_btn = QPushButton("🌙 Dark Theme")
        self.theme_toggle_btn.setFixedHeight(30)
        self.theme_toggle_btn.setFixedWidth(120)
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        theme_layout.addWidget(self.theme_toggle_btn)
        theme_layout.addStretch()
        main_layout.addLayout(theme_layout)

        
        self.is_dark_theme = True  # Start with dark 

        # Button area
        button_layout = QHBoxLayout()

        self.execute_btn = QPushButton("Start Packaging")
        self.execute_btn.setFixedHeight(40)
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.execute_btn.clicked.connect(self.execute_package)

        self.stop_btn = QPushButton("Stop Packaging")
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_package)
        self.stop_btn.setEnabled(False)

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.setFixedHeight(40)
        self.clear_btn.clicked.connect(self.clear_log)

        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.clear_btn)

        main_layout.addLayout(button_layout)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready - Configure packaging options")
    def toggle_theme(self):
        """Toggle between dark and light themes"""
        self.is_dark_theme = not self.is_dark_theme
        
        # Update button text and icon
        if self.is_dark_theme:
            self.theme_toggle_btn.setText("🌙 Dark Theme")
        else:
            self.theme_toggle_btn.setText("☀️ Light Theme")
        
        # Apply the new theme
        self.set_style()
        
        # Log the theme change
        theme_name = "Dark" if self.is_dark_theme else "Light"
        self.log_message(f"🎨 Switched to {theme_name} theme")

    def add_python_flag(self):
        """Add Python flag to list"""
        flag = self.flags_combo.currentText()
        if flag and not self.flag_exists(flag):
            self.flags_list.addItem(flag)
            self.update_command()

    def remove_python_flag(self):
        """Remove selected Python flag"""
        selected_items = self.flags_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            self.flags_list.takeItem(self.flags_list.row(item))
        self.update_command()

    def toggle_remove_button(self):
        """Enable/disable remove button based on selection"""
        self.remove_flag_btn.setEnabled(bool(self.flags_list.selectedItems()))

    def flag_exists(self, flag):
        """Check if flag already exists"""
        for i in range(self.flags_list.count()):
            if self.flags_list.item(i).text() == flag:
                return True
        return False

    def set_style(self):
        """Seted application styling based on theme"""
        if self.is_dark_theme:
            # Dark Theme
            main_bg = """
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0d0d0f,
                    stop: 0.4 #1a1a1f,
                    stop: 0.7 #0f1f2f,
                    stop: 1 #0d0d0f
                );
            }
            """
            
            style = """
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 8px;
                margin-top: 1.5em;
                background-color: #333;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: transparent;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QLineEdit, QComboBox, QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QLineEdit:disabled, QTextEdit:disabled {
                background-color: #444;
                color: #888;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #666;
            }
            QLabel {
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                border-radius: 5px;
                background: #333;
            }
            QTabBar::tab {
                background: #444;
                border: 1px solid #555;
                border-bottom: none;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                color: #ffffff;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
            QTabBar::tab:hover {
                background: #2980b9;
                color: white;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
                border-radius: 3px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QSpinBox {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            """
            
            self.setStyleSheet(main_bg)
            self.centralWidget().setStyleSheet(style)
            
        else:
            # Light Theme
            style = """
            QMainWindow {
                background-color: #f5f7fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dcdde1;
                border-radius: 8px;
                margin-top: 1.5em;
                background-color: white;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: transparent;
                color: #2c3e50;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 5px;
                color: #2c3e50;
            }
            QLineEdit, QComboBox, QListWidget {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 5px;
                color: #2c3e50;
            }
            QLineEdit:disabled, QTextEdit:disabled {
                background-color: #ecf0f1;
                color: #7f8c8d;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QLabel {
                color: #2c3e50;
            }
            QProgressBar {
                border: 1px solid #dcdde1;
                border-radius: 5px;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #dcdde1;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                border: 1px solid #dcdde1;
                border-bottom: none;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                color: #2c3e50;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
            QTabBar::tab:hover {
                background: #2980b9;
                color: white;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
                border-radius: 3px;
            }
            QCheckBox {
                color: #2c3e50;
            }
            QSpinBox {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 5px;
                color: #2c3e50;
            }
            """
            
            self.setStyleSheet(style)

    def log_message(self, message):
        """Add message to log box"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_edit.append(f"[{timestamp}] {message}")
        self.log_edit.moveCursor(QTextCursor.End)

        # Show last message in status bar
        self.status_bar.showMessage(message)

    def select_python(self):
        """Select Python interpreter"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Python Interpreter", "", "Python Interpreter (python.exe python.cmd);;All Files (*)"
        )
        if file_path:
            self.python_path = file_path
            self.python_input.setText(file_path)

            # Check if Nuitka is installed
            if not self.check_nuitka_installed():
                QMessageBox.warning(
                    self,
                    "Nuitka Not Installed",
                    "Nuitka not detected in selected Python environment.\nInstall with: pip install nuitka",
                    QMessageBox.Ok
                )
            else:
                self.log_message("✓ Nuitka installed in selected Python environment")

    def check_nuitka_installed(self):
        """Check if Nuitka is installed in selected Python environment"""
        try:
            # Method 1: Check if interpreter path contains 'nuitka'
            if "nuitka" in self.python_path.lower():
                return True

            # Method 2: Most reliable - try running nuitka --version
            try:
                result = subprocess.run(
                    [self.python_path, "-m", "nuitka", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            # Method 3: Check virtual environment's executable directory
            # Get virtual environment base directory
            env_base = os.path.dirname(os.path.dirname(self.python_path))

            # Determine scripts directory name (Windows: Scripts, Unix: bin)
            scripts_dir = "Scripts" if sys.platform.startswith("win") else "bin"
            scripts_path = os.path.join(env_base, scripts_dir)

            # Check for possible executables
            for exe_name in ["nuitka", "nuitka.exe", "nuitka.cmd", "nuitka-script.py"]:
                exe_path = os.path.join(scripts_path, exe_name)
                if os.path.exists(exe_path):
                    return True

            # Method 4: Check package metadata (compatible with uv/pip)
            # Try uv first, then pip
            for module in ["uv", "pip"]:
                try:
                    result = subprocess.run(
                        [self.python_path, "-m", module, "show", "nuitka"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=2,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    # Check if successful and contains package info
                    if result.returncode == 0 and "Name: nuitka" in result.stdout:
                        return True
                except:
                    continue

            return False
        except Exception:
            return False

    def select_main_file(self):
        """Select main Python file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Main Python File", "", "Python Files (*.py);;All Files (*)"
        )
        if file_path:
            self.main_file = file_path
            self.file_input.setText(file_path)

    def select_icon(self):
        """Select icon file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon File", "", "Icon Files (*.ico);;All Files (*)"
        )
        if file_path:
            self.icon_file = file_path
            self.icon_input.setText(file_path)

    def select_output_dir(self):
        """Select output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.output_dir = dir_path
            self.output_input.setText(dir_path)

    def update_command(self):
        """Update packaging command based on user selections"""
        if not self.python_path or not self.main_file:
            self.command_edit.setPlainText("1. Select Python interpreter and main file \n2. Configure options to update command")
            return

        # Build base command
        command = [
            self.python_path,
            "-m", "nuitka"
        ]

        # For uv environments, use nuitka.cmd directly
        if self.python_path.endswith("nuitka.cmd"):
            command = [self.python_path]

        # ===== Common Options =====
        if self.onefile_check.isChecked():
            command.append("--onefile")

        if self.standalone_check.isChecked():
            command.append("--standalone")

        if self.disable_console_check.isChecked():
            command.append("--windows-disable-console")

        if self.remove_output_check.isChecked():
            command.append("--remove-output")

        if self.include_qt_check.isChecked():
            command.append("--include-qt-plugins=sensible,styles")

        if self.show_progress_check.isChecked():
            command.append("--show-progress")

        if self.show_memory_check.isChecked():
            command.append("--show-memory")

        # Add icon
        if self.icon_file:
            command.append(f"--windows-icon-from-ico={self.icon_file}")

        # Add output directory
        if self.output_dir:
            command.append(f"--output-dir={self.output_dir}")

        # ===== Plugin Options =====
        selected_plugins = [item.text().split('=')[1] for item in self.plugins_list.selectedItems()]
        for plugin in selected_plugins:
            command.append(f"--enable-plugin={plugin}")

        # ===== Advanced Options =====
        if self.follow_imports_check.isChecked():
            command.append("--follow-imports")

        if self.follow_stdlib_check.isChecked():
            command.append("--follow-stdlib")

        if self.module_mode_check.isChecked():
            command.append("--module")

        if self.lto_check.isChecked():
            command.append("--lto")

        if self.disable_ccache_check.isChecked():
            command.append("--disable-ccache")

        if self.assume_yes_check.isChecked():
            command.append("--assume-yes")

        if self.windows_uac_admin_check.isChecked():
            command.append("--windows-uac-admin")

        if self.windows_uac_uiaccess_check.isChecked():
            command.append("--windows-uac-uiaccess")

        # ===== Include Options =====
        # Include packages
        if self.include_package_input.text():
            packages = [pkg.strip() for pkg in self.include_package_input.text().split(',') if pkg.strip()]
            for pkg in packages:
                command.append(f"--include-package={pkg}")

        # Include package data
        if self.include_package_data_input.text():
            package_data = [pd.strip() for pd in self.include_package_data_input.text().split(',') if pd.strip()]
            for pd in package_data:
                command.append(f"--include-package-data={pd}")

        # Include modules
        if self.include_module_input.text():
            modules = [mod.strip() for mod in self.include_module_input.text().split(',') if mod.strip()]
            for mod in modules:
                command.append(f"--include-module={mod}")

        # Include data directories
        if self.include_data_dir_input.text():
            data_dirs = [dd.strip() for dd in self.include_data_dir_input.text().split(',') if dd.strip()]

            # Get project base path from main file location
            if not self.main_file:
                QMessageBox.warning(self, "Warning", "Please select main file first")
                return

            project_base_dir = os.path.dirname(self.main_file)

            for dd in data_dirs:
                # Split source and destination paths
                if '=' in dd:
                    src_path, dest_path = dd.split('=', 1)
                else:
                    src_path = dd
                    # Default destination is last part of source path
                    dest_path = os.path.basename(src_path)

                # Ensure source path is absolute
                if not os.path.isabs(src_path):
                    # Resolve relative path based on main file directory
                    resolved_path = os.path.join(project_base_dir, src_path)

                    # Verify path exists
                    if os.path.exists(resolved_path):
                        src_path = resolved_path
                    else:
                        logging.warning(f"Resource path does not exist: {resolved_path}")
                        continue

                # Verify path exists
                if not os.path.exists(src_path):
                    logging.warning(f"Include data directory not found: {src_path}")
                    continue

                # Add to command
                command.append(f"--include-data-dir={src_path}={dest_path}")
                logging.info(f"Added include directory: {src_path} -> {dest_path}")

                # Detailed logging
                logging.debug(f"Original input: {dd}")
                logging.debug(f"Resolved source: {src_path}")
                logging.debug(f"Resolved destination: {dest_path}")

        # Exclude data files
        if self.noinclude_data_input.text():
            exclude_data = [ed.strip() for ed in self.noinclude_data_input.text().split(',') if ed.strip()]
            for ed in exclude_data:
                command.append(f"--noinclude-data-files={ed}")

        # Onefile external data (only when onefile mode is enabled)
        if self.onefile_check.isChecked() and self.include_onefile_ext_input.text():
            onefile_ext = [oe.strip() for oe in self.include_onefile_ext_input.text().split(',') if oe.strip()]
            for oe in onefile_ext:
                command.append(f"--include-onefile-external-data={oe}")

        # Include raw directories
        if self.include_raw_dir_input.text():
            raw_dirs = [rd.strip() for rd in self.include_raw_dir_input.text().split(',') if rd.strip()]
            for rd in raw_dirs:
                command.append(f"--include-raw-dir={rd}")

        # ===== Python Flags =====
        for i in range(self.flags_list.count()):
            command.append(self.flags_list.item(i).text())

        # ===== Onefile Options =====
        if self.onefile_check.isChecked():
            if self.onefile_tempdir_input.text():
                command.append(f"--onefile-tempdir-spec={self.onefile_tempdir_input.text()}")

            if self.onefile_grace_time_spin.value() != 5000:
                command.append(f"--onefile-child-grace-time={self.onefile_grace_time_spin.value()}")

            if self.onefile_no_compression_check.isChecked():
                command.append("--onefile-no-compression")

            if self.onefile_as_archive_check.isChecked():
                command.append("--onefile-as-archive")

        # ===== DLL Control =====
        if self.noinclude_dlls_input.text():
            command.append(f"--noinclude-dlls={self.noinclude_dlls_input.text()}")

        # ===== Metadata =====
        if self.company_input.text():
            command.append(f"--company-name={self.company_input.text()}")

        if self.product_input.text():
            command.append(f"--product-name={self.product_input.text()}")

        if self.file_version_input.text():
            command.append(f"--file-version={self.file_version_input.text()}")

        if self.product_version_input.text():
            command.append(f"--product-version={self.product_version_input.text()}")

        if self.file_description_input.text():
            command.append(f"--file-description={self.file_description_input.text()}")

        if self.copyright_input.text():
            command.append(f"--copyright={self.copyright_input.text()}")

        # ===== Environment Control =====
        if self.force_env_input.text():
            command.append(f"--force-runtime-environment-variable={self.force_env_input.text()}")

        # ===== Debug Options =====
        if self.debug_check.isChecked():
            command.append("--debug")

        if self.unstripped_check.isChecked():
            command.append("--unstripped")

        if self.trace_execution_check.isChecked():
            command.append("--trace-execution")

        if self.warn_implicit_check.isChecked():
            command.append("--warn-implicit-exceptions")

        if self.warn_unusual_check.isChecked():
            command.append("--warn-unusual-code")

        if self.deployment_check.isChecked():
            command.append("--deployment")

        # Add main file
        command.append(self.main_file)

        # Display command
        self.command_edit.setPlainText(" ".join(command))

    def execute_package(self):
        """Execute packaging command"""
        # Check if packaging thread is already running
        if self.package_thread and self.package_thread.isRunning():
            self.log_message("⚠️ Packaging already in progress")
            return

        # Validate required inputs
        if not self.python_path:
            QMessageBox.warning(self, "Missing Configuration", "Select Python interpreter")
            return

        if not self.main_file:
            QMessageBox.warning(self, "Missing Configuration", "Select main file")
            return

        if not self.output_dir:
            QMessageBox.warning(self, "Missing Configuration", "Select output directory")
            return

        # Check if Nuitka is installed
        if not self.check_nuitka_installed():
            QMessageBox.warning(
                self,
                "Nuitka Not Installed",
                "Nuitka not detected in selected Python environment.\nInstall with: pip install nuitka",
                QMessageBox.Ok
            )
            return

        # Get command
        command = self.command_edit.toPlainText().split()

        # Create and start packaging thread
        self.package_thread = PackageThread(command)
        self.package_thread.log_signal.connect(self.log_message)
        self.package_thread.finished_signal.connect(self.package_finished)

        # Update UI state
        self.execute_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        # Start thread
        self.package_thread.start()
        self.log_message("▶ Starting packaging process...")

        # Simulate progress updates
        self.progress_timer = self.startTimer(1000)

        # Auto-switch to log tab
        main_tab = self.findChild(QTabWidget)
        if main_tab:
            for i in range(main_tab.count()):
                if main_tab.tabText(i) == "Operation Log":
                    main_tab.setCurrentIndex(i)
                    break

    def timerEvent(self, event):
        """Timer event for progress bar updates"""
        if self.progress_bar.value() < 90:
            self.progress_bar.setValue(self.progress_bar.value() + 5)

    def stop_package(self):
        """Stop packaging process"""
        if self.package_thread and self.package_thread.isRunning():
            self.package_thread.stop()
            self.log_message("🛑 User requested packaging stop...")
            self.stop_btn.setEnabled(False)

            # Attempt normal thread termination
            if not self.package_thread.wait(2000):  # Wait 2 seconds
                # Force terminate if still running
                self.package_thread.terminate()
                self.log_message("⚠️ Forced packaging thread termination")

            # Reset button state immediately
            self.execute_btn.setEnabled(True)
            self.progress_bar.setValue(0)

            # Stop progress updates
            if hasattr(self, 'progress_timer'):
                self.killTimer(self.progress_timer)

    def package_finished(self, success):
        """Handle packaging completion"""
        # Always update UI state
        self.execute_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # Complete progress bar
        self.progress_bar.setValue(100 if success else 0)

        # Stop progress updates
        if hasattr(self, 'progress_timer'):
            self.killTimer(self.progress_timer)

        if success:
            self.log_message("✅ Packaging completed successfully!")
            self.log_message(f"Output directory: {self.output_dir}")

            # Ask to open output directory
            reply = QMessageBox.question(
                self,
                "Packaging Success",
                "Packaging completed! Open output directory?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                os.startfile(self.output_dir)
        else:
            self.log_message("❌ Errors occurred during packaging, check log")

    def clear_log(self):
        """Clear log"""
        self.log_edit.clear()
        self.log_message("Log cleared")
        self.progress_bar.setValue(0)

    def closeEvent(self, event):
        """Handle window close event"""
        if self.package_thread and self.package_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Packaging In Progress",
                "Packaging is still running. Exit anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.package_thread.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NuitkaPackager()
    window.show()
    sys.exit(app.exec())