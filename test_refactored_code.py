"""
Basic test to verify the refactored modules work correctly.
"""

def test_imports():
    """Test that all modules can be imported without errors."""
    try:
        from src.config.settings import ConfigManager
        from src.models.transcriber import AudioTranscriber
        from src.core.note_generator import NoteGenerator
        from src.utils.helpers import get_timestamped_filename
        from src.workers.processing_worker import ProcessingWorker
        from src.ui.main_window import MainWindow

        print("[OK] All modules imported successfully")
        return True
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality of key modules."""
    try:
        # Test config manager
        from src.config.settings import ConfigManager
        config = ConfigManager()
        print("[OK] ConfigManager instantiated successfully")

        # Test utility function
        from src.utils.helpers import get_timestamped_filename
        filename = get_timestamped_filename("test", "txt")
        assert filename.startswith("test_")
        assert filename.endswith(".txt")
        print("[OK] get_timestamped_filename works correctly")

        # Test note generator (doesn't require Ollama to be running for instantiation)
        from src.core.note_generator import NoteGenerator
        generator = NoteGenerator()
        print("[OK] NoteGenerator instantiated successfully")

        print("[OK] Basic functionality tests passed")
        return True
    except Exception as e:
        print(f"[ERROR] Basic functionality test failed: {e}")
        return False


if __name__ == "__main__":
    print("Running basic tests on refactored modules...\n")

    success = True
    success &= test_imports()
    success &= test_basic_functionality()

    if success:
        print("\n[SUCCESS] All tests passed! The refactored code appears to be working correctly.")
    else:
        print("\n[FAILURE] Some tests failed. Please check the implementation.")