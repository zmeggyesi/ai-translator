# Design Document

## Overview

The Translation GUI is a desktop application built using Tkinter (Python's standard GUI library) that provides a user-friendly interface for the existing CLI-based translation pipeline. The design prioritizes simplicity, accessibility, and visual appeal while maintaining full feature parity with the command-line interface.

The application follows a tabbed interface pattern with dedicated sections for translation, style extraction, glossary management, and resource administration. The design emphasizes progressive disclosure, showing basic options by default with advanced features accessible through expandable sections.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI Application Layer                    │
├─────────────────────────────────────────────────────────────────┤
│  Main Window  │  Translation Tab  │  Style Tab  │  Glossary Tab │
│  Controller   │  Controller       │  Controller │  Controller   │
├─────────────────────────────────────────────────────────────────┤
│                     Service Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  Translation  │  Style Extract  │  Glossary    │  Resource      │
│  Service      │  Service        │  Service     │  Manager       │
├─────────────────────────────────────────────────────────────────┤
│                    Existing CLI Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  cli.py       │  nodes/         │  graph.py    │  state.py      │
│  functions    │  modules        │  workflow    │  definitions   │
└─────────────────────────────────────────────────────────────────┘
```

### Framework Selection

**Primary Framework: Tkinter with ttk**
- **Rationale**: Built into Python standard library, no additional dependencies
- **Benefits**: Cross-platform compatibility, mature and stable, lightweight
- **Styling**: Modern ttk themes for professional appearance

**Alternative Considered: CustomTkinter**
- **Benefits**: Modern flat design, better visual appeal
- **Trade-off**: Additional dependency vs. built-in solution
- **Decision**: Start with ttk, upgrade to CustomTkinter if visual requirements demand it

### Design Patterns

1. **Model-View-Controller (MVC)**
   - Models: Data classes wrapping TranslationState and configuration
   - Views: Tkinter widgets and frames
   - Controllers: Event handlers and business logic coordinators

2. **Observer Pattern**
   - Progress updates and status changes broadcast to UI components
   - Real-time updates during long-running operations

3. **Command Pattern**
   - All user actions encapsulated as commands for undo/redo capability
   - Consistent error handling and logging

## Components and Interfaces

### Main Application Window

```python
class TranslationGUI:
    """Main application window with tabbed interface"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.notebook = ttk.Notebook()
        self.config_manager = ConfigurationManager()
        self.setup_ui()
        
    def setup_ui(self):
        # Configure main window
        # Create tabbed interface
        # Initialize tab controllers
        # Setup menu bar and status bar
```

**Key Features:**
- Tabbed interface using ttk.Notebook
- Menu bar with File, Edit, View, Help menus
- Status bar with progress indicators
- Keyboard shortcuts for common operations
- Window state persistence

### Translation Tab Controller

```python
class TranslationTabController:
    """Handles translation workflow UI and logic"""
    
    def __init__(self, parent_frame):
        self.frame = parent_frame
        self.translation_service = TranslationService()
        self.setup_translation_ui()
        
    def setup_translation_ui(self):
        # File selection section
        # Language configuration section
        # Optional resources section (collapsible)
        # Translation options section
        # Progress and results section
```

**UI Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Input File: [Browse...] [file_path_display]                │
├─────────────────────────────────────────────────────────────┤
│ Source Language: [Dropdown ▼] Target Language: [Dropdown ▼]│
├─────────────────────────────────────────────────────────────┤
│ ▼ Optional Resources (Click to expand)                     │
│   Glossary: [Browse...] [Use Default] [path_display]       │
│   Style Guide: [Browse...] [Use Default] [path_display]    │
│   TMX Memory: [Browse...] [None] [path_display]            │
├─────────────────────────────────────────────────────────────┤
│ ☐ Enable Review  ☐ Generate Visualizations                 │
│ [Translate] [Clear] [Save Settings]                        │
├─────────────────────────────────────────────────────────────┤
│ Progress: [████████████████████████████] 100%              │
│ Status: Translation completed successfully                   │
├─────────────────────────────────────────────────────────────┤
│ Original Text          │ Translated Text                    │
│ [scrollable_text_area] │ [scrollable_text_area]            │
│                        │ [Save Translation] [Copy]          │
└─────────────────────────────────────────────────────────────┘
```

### Style Extraction Tab Controller

```python
class StyleExtractionTabController:
    """Handles style guide extraction UI and logic"""
    
    def __init__(self, parent_frame):
        self.frame = parent_frame
        self.style_service = StyleExtractionService()
        self.setup_style_ui()
```

**UI Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Input File: [Browse...] [file_path_display]                │
│ File Type: ○ Auto-detect ○ TMX ○ PDF ○ DOCX ○ DOC          │
├─────────────────────────────────────────────────────────────┤
│ Source Language: [Dropdown ▼]                              │
│ Target Language: [Dropdown ▼] (Required for TMX)           │
├─────────────────────────────────────────────────────────────┤
│ Output File: [Browse...] [output_path_display]             │
│ [Extract Style Guide] [Clear]                              │
├─────────────────────────────────────────────────────────────┤
│ Progress: [████████████████████████████] 100%              │
├─────────────────────────────────────────────────────────────┤
│ Generated Style Guide Preview:                              │
│ [scrollable_markdown_preview]                              │
│ [Save] [Copy] [Edit]                                       │
└─────────────────────────────────────────────────────────────┘
```

### Glossary Management Tab Controller

```python
class GlossaryTabController:
    """Handles glossary extraction and management UI"""
    
    def __init__(self, parent_frame):
        self.frame = parent_frame
        self.glossary_service = GlossaryService()
        self.setup_glossary_ui()
```

**UI Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Extract From: ○ TMX File ○ Text File                       │
│ Input File: [Browse...] [file_path_display]                │
├─────────────────────────────────────────────────────────────┤
│ Source Language: [Dropdown ▼] Target Language: [Dropdown ▼]│
│ Output File: [Browse...] [output_path_display]             │
│ [Extract Glossary] [Load Existing] [New Glossary]          │
├─────────────────────────────────────────────────────────────┤
│ Glossary Editor:                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Term            │ Translation      │ Actions           │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ [editable_cell] │ [editable_cell] │ [Edit] [Delete]   │ │
│ │ [editable_cell] │ [editable_cell] │ [Edit] [Delete]   │ │
│ │ ...             │ ...             │ ...               │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [Add Term] [Import CSV] [Export CSV] [Save]                 │
└─────────────────────────────────────────────────────────────┘
```

### Resource Management Tab Controller

```python
class ResourceManagerController:
    """Handles centralized resource management"""
    
    def __init__(self, parent_frame):
        self.frame = parent_frame
        self.resource_service = ResourceManagerService()
        self.setup_resource_ui()
```

## Data Models

### Configuration Models

```python
@dataclass
class TranslationConfig:
    """Configuration for translation operations"""
    input_file: str
    source_language: str
    target_language: str
    glossary_file: Optional[str] = None
    style_guide_file: Optional[str] = None
    tmx_file: Optional[str] = None
    enable_review: bool = False
    generate_visualizations: bool = False
    
    def to_cli_args(self) -> List[str]:
        """Convert to CLI arguments for backend execution"""
        pass

@dataclass
class StyleExtractionConfig:
    """Configuration for style guide extraction"""
    input_file: str
    file_type: str
    source_language: str
    target_language: Optional[str] = None
    output_file: str

@dataclass
class GlossaryConfig:
    """Configuration for glossary operations"""
    source_type: str  # 'tmx' or 'text'
    input_file: str
    source_language: str
    target_language: str
    output_file: str

@dataclass
class ApplicationState:
    """Persistent application state"""
    last_used_tab: int
    window_geometry: str
    recent_files: List[str]
    default_languages: Tuple[str, str]
    resource_paths: Dict[str, str]
```

### UI State Models

```python
class ProgressState:
    """Tracks progress of long-running operations"""
    current_step: str
    progress_percentage: float
    is_running: bool
    can_cancel: bool
    
class ReviewDialogState:
    """State for interactive review dialogs"""
    original_text: str
    translated_text: str
    review_scores: Dict[str, float]
    review_explanations: Dict[str, str]
    user_modifications: Dict[str, str]
```

## Error Handling

### Error Categories

1. **File System Errors**
   - File not found, permission denied, invalid format
   - User-friendly messages with suggested actions
   - Automatic fallback to default resources when possible

2. **Configuration Errors**
   - Invalid language codes, missing required fields
   - Real-time validation with inline error messages
   - Smart defaults and auto-correction suggestions

3. **Processing Errors**
   - API failures, network issues, processing timeouts
   - Graceful degradation with retry mechanisms
   - Detailed error logs for troubleshooting

4. **Resource Errors**
   - Corrupted TMX files, invalid glossary format
   - Validation with specific error descriptions
   - Recovery options and format conversion tools

### Error Handling Strategy

```python
class ErrorHandler:
    """Centralized error handling and user notification"""
    
    @staticmethod
    def handle_file_error(error: FileNotFoundError, context: str):
        """Handle file-related errors with user-friendly messages"""
        pass
        
    @staticmethod
    def handle_processing_error(error: Exception, operation: str):
        """Handle processing errors with retry options"""
        pass
        
    @staticmethod
    def show_error_dialog(title: str, message: str, details: str = None):
        """Display error dialog with optional details"""
        pass
```

## Testing Strategy

### Unit Testing

1. **Controller Testing**
   - Mock UI components and test business logic
   - Validate configuration generation and validation
   - Test error handling and edge cases

2. **Service Layer Testing**
   - Mock CLI backend and test service integration
   - Test progress tracking and cancellation
   - Validate data transformation and persistence

3. **Model Testing**
   - Test configuration serialization/deserialization
   - Validate data model constraints and validation
   - Test state management and persistence

### Integration Testing

1. **UI Integration**
   - Test complete user workflows end-to-end
   - Validate UI state synchronization
   - Test keyboard shortcuts and accessibility

2. **Backend Integration**
   - Test CLI integration with real backend
   - Validate file handling and resource management
   - Test error propagation and recovery

### User Acceptance Testing

1. **Usability Testing**
   - Test with non-technical users
   - Validate intuitive workflow and error recovery
   - Measure task completion times and success rates

2. **Compatibility Testing**
   - Test across different operating systems
   - Validate with various file formats and sizes
   - Test with different screen resolutions and DPI settings

## Performance Considerations

### Responsive UI Design

1. **Asynchronous Operations**
   - All long-running operations run in background threads
   - UI remains responsive during processing
   - Real-time progress updates and cancellation support

2. **Memory Management**
   - Lazy loading of large files and resources
   - Efficient text widget handling for large documents
   - Automatic cleanup of temporary files and resources

3. **Startup Performance**
   - Fast application startup with lazy initialization
   - Background loading of resources and configurations
   - Progressive UI rendering for immediate user feedback

### Scalability

1. **Large File Handling**
   - Streaming file processing for large documents
   - Chunked text display with virtual scrolling
   - Memory-efficient resource caching

2. **Batch Processing**
   - Queue-based job management
   - Parallel processing where possible
   - Progress aggregation and error isolation

## Security Considerations

### File System Security

1. **Path Validation**
   - Sanitize all file paths to prevent directory traversal
   - Validate file extensions and MIME types
   - Restrict access to system directories

2. **Temporary File Management**
   - Secure temporary file creation and cleanup
   - Proper file permissions and access controls
   - Automatic cleanup on application exit

### API Security

1. **Credential Management**
   - Secure storage of API keys and credentials
   - Environment variable integration
   - User notification for missing credentials

2. **Network Security**
   - Validate SSL certificates for API calls
   - Implement request timeouts and retry limits
   - Log security-relevant events for auditing