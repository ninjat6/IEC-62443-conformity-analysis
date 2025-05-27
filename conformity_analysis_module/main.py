# conformity_analysis_module/main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from .gui.main_window import ConformityAnalysisWindow
from .gui.progress_dialog import ModelDownloadProgressDialog
from .core.model_manager import ModelManager
from .utils.logger import logger
# import logging # Only if logger from .utils is not available/working early

# The sys.path modification block has been removed.

class ProgressEmitter(QObject):
    """
    A QObject subclass designed to emit signals for progress updates.
    This is useful for relaying information from a potentially non-GUI context
    (like the ModelManager performing downloads) to GUI elements (like ModelDownloadProgressDialog)
    in a thread-safe manner, as signals/slots are a core Qt mechanism for inter-object communication.
    """
    # Signal to emit a new progress message (string).
    new_message = pyqtSignal(str)
    # Signal to indicate the overall process has finished.
    # The boolean argument indicates success (True) or failure (False).
    finished = pyqtSignal(bool) 

class ConformityAnalysis:
    """
    ConformityAnalysis 是整合所有功能的主要入口，
    其他程式只需實例化此類別並呼叫 run()，即可啟動完整的文件搜尋工具。
    """
    def __init__(self):
        # QApplication must be created before any QDialog or QWidget can be shown.
        # `QApplication.instance()` retrieves the existing QApplication instance if one exists.
        # If no instance exists (e.g., when running this module standalone or as the primary entry point),
        # `QApplication(sys.argv)` creates a new one. This ensures that there's always one,
        # and only one, QApplication instance.
        self.app = QApplication.instance() 
        if self.app is None: 
            self.app = QApplication(sys.argv)

        # Instantiate the ProgressEmitter to bridge ModelManager progress to the GUI dialog.
        progress_emitter = ProgressEmitter()
        # Instantiate the ModelDownloadProgressDialog. It's a modal dialog that will
        # show progress messages for model downloads. Parent is None, making it a top-level window.
        progress_dialog = ModelDownloadProgressDialog() 

        # Connect the signals from the ProgressEmitter to the slots of the ModelDownloadProgressDialog.
        # - When `progress_emitter.new_message` is emitted, `progress_dialog.update_progress` slot is called.
        progress_emitter.new_message.connect(progress_dialog.update_progress)
        # - When `progress_emitter.finished` is emitted, `progress_dialog.mark_finished` slot is called.
        progress_emitter.finished.connect(progress_dialog.mark_finished)
        # The ModelDownloadProgressDialog itself connects its `request_close` signal to its `accept()` slot,
        # which handles closing the dialog.

        # Show the progress dialog.
        progress_dialog.show()
        # Call `QApplication.processEvents()` immediately after `show()` to ensure the dialog
        # is displayed and painted promptly before the potentially blocking model download process begins.
        # This provides immediate visual feedback to the user.
        QApplication.processEvents() 

        # Define the callback function that ModelManager's `ensure_all_models_available` will use.
        # This callback will be invoked by ModelManager with progress messages.
        def model_progress_callback(message: str):
            # Emit the `new_message` signal from our `progress_emitter`.
            # This will, in turn, call `progress_dialog.update_progress` due to the connection made above.
            progress_emitter.new_message.emit(message)
            # Note: `QApplication.processEvents()` is now handled within `dialog.update_progress`
            # to ensure each message is updated in the dialog's QTextEdit.

        logger.info("Ensuring all models are available before GUI initialization. Progress dialog is active.")
        model_manager = ModelManager()
        
        # Call ModelManager to ensure all models are downloaded/validated.
        # The `model_progress_callback` will relay progress to the dialog via the emitter.
        all_models_ready = model_manager.ensure_all_models_available(progress_callback=model_progress_callback)
        
        # Signal that the overall model processing is finished, passing the success status.
        # This will trigger `progress_dialog.mark_finished`.
        progress_emitter.finished.emit(all_models_ready)
        
        # Attempt to ensure the dialog closes cleanly after `mark_finished` (which emits `request_close`).
        # The `request_close` signal is connected to `dialog.accept()`.
        # This loop gives the event loop some cycles to process the close request.
        # It's a safeguard for scenarios where the dialog might not close immediately
        # due to event loop timing, especially if the subsequent main window setup is heavy.
        close_loop_count = 0
        while progress_dialog.isVisible() and close_loop_count < 200: # Max ~2 seconds timeout (200 * 0.01s if sleep was used)
            QApplication.processEvents() # Allow Qt to process events, including the dialog close.
            # A small, non-blocking delay could be added here if strictly necessary,
            # but frequent processEvents is generally preferred over time.sleep in GUI threads.
            # Example: `QtCore.QTimer.singleShot(10, lambda: None)` could yield control.
            close_loop_count += 1
        
        # If the dialog is still visible after the loop (which is unlikely but possible), force it closed.
        if progress_dialog.isVisible():
            logger.warning("Progress dialog did not auto-close as expected. Forcing close.")
            progress_dialog.close()

        # Handle the case where models are not ready.
        if not all_models_ready:
            logger.error("One or more models could not be made available. Application may not function correctly.")
            # At this point, the application could show a critical error message to the user
            # (e.g., using QMessageBox) and potentially exit, or proceed with limited functionality.
            # The current implementation lets it proceed, and the Analyzer will likely raise a
            # RuntimeError if its required model is missing, which should be caught by the root main.py.
            # Example:
            # from PyQt6.QtWidgets import QMessageBox
            # QMessageBox.critical(None, "Model Download Error", 
            #                      "Failed to download all necessary models. The application might not function correctly. Please check logs.")

        logger.info("Proceeding with main ConformityAnalysisWindow initialization...")
        # Initialize the main application window now that model checks are complete.
        self.window = ConformityAnalysisWindow()

    def run(self):
        """啟動應用程式"""
        if hasattr(self, 'window') and self.window:
            self.window.show()
            sys.exit(self.app.exec())
        else:
            logger.critical("Main window (ConformityAnalysisWindow) was not initialized. This might be due to critical model loading failures or other pre-GUI setup issues. Exiting.")
            if QApplication.instance(): # Ensure we quit QApplication if it was started
                 QApplication.instance().quit()
            sys.exit(1)

# 僅在獨立執行時啟動
if __name__ == "__main__":
    app = ConformityAnalysis()
    app.run()