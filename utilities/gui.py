"""
Medieval-themed GUI for Our Legacy RPG using customtkinter.
Provides a complete GUI-based interface for the game.
"""

import customtkinter as ctk
from typing import Callable, Optional, List, Dict, Any
import tkinter as tk
from tkinter import messagebox
import threading

# Medieval color palette
MEDIEVAL_COLORS = {
    'bg_dark': '#1a1a1a',
    'bg_darker': '#0d0d0d',
    'bg_light': '#2d2d2d',
    'accent_gold': '#d4af37',
    'accent_red': '#8b0000',
    'text_light': '#e8d5c4',
    'text_dim': '#8b8b7a',
    'border_gold': '#6b5d47',
    'health_red': '#cc0000',
    'mana_blue': '#0066cc',
    'exp_green': '#00cc00',
    'gold_yellow': '#ffd700',
}

# Rarity colors
RARITY_COLORS = {
    'common': '#ffffff',
    'uncommon': '#92D050',
    'rare': '#4472C4',
    'epic': '#7030A0',
    'legendary': '#FFD700',
}


class MedievalWindow(ctk.CTk):
    """
    Main medieval-themed window for the game.
    """
    
    def __init__(self, title: str = "Our Legacy", width: int = 1000, height: int = 700):
        """
        Initialize the medieval window.
        
        Args:
            title: Window title
            width: Window width in pixels
            height: Window height in pixels
        """
        super().__init__()

        self.title(title)
        self.geometry(f"{width}x{height}")
        self.minsize(800, 600)

        # Configure color scheme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Configure window background
        self.configure(fg_color=MEDIEVAL_COLORS['bg_dark'])

        # Initialize frames
        self.main_frame: Optional[ctk.CTkFrame] = None
        self.setup_main_frame()

    def setup_main_frame(self):
        """Setup the main content frame."""
        self.main_frame = ctk.CTkFrame(self,
                                       fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

    def clear_frame(self, frame: Optional[ctk.CTkFrame] = None):
        """Clear all widgets from a frame."""
        target_frame = frame if frame is not None else self.main_frame

        if target_frame is None:
            return

        for widget in target_frame.winfo_children():
            widget.destroy()

    def get_main_frame(self) -> Optional[ctk.CTkFrame]:
        """Get the main content frame."""
        return self.main_frame


class MedievalButton(ctk.CTkButton):
    """
    Medieval-themed button with ornate styling.
    """

    def __init__(
            self,
            master,
            text: str = "Button",
            command: Optional[Callable] = None,
            size: str = "normal",
            **kwargs):
        """
        Initialize a medieval-themed button.

        Args:
            master: Parent widget
            text: Button text
            command: Callback function when clicked
            size: Button size ('small', 'normal', 'large')
        """
        font_sizes = {
            'small': 12,
            'normal': 14,
            'large': 16,
        }

        font_size = font_sizes.get(size, 14)

        super().__init__(master,
                         text=text,
                         command=command,
                         fg_color=MEDIEVAL_COLORS['accent_red'],
                         hover_color='#a00000',
                         text_color=MEDIEVAL_COLORS['text_light'],
                         font=('Arial', font_size, 'bold'),
                         border_width=2,
                         border_color=MEDIEVAL_COLORS['accent_gold'],
                         corner_radius=8,
                         **kwargs)


class MedievalLabel(ctk.CTkLabel):
    """
    Medieval-themed label with ornate styling.
    """

    def __init__(self,
                 master,
                 text: str = "Label",
                 style: str = "normal",
                 **kwargs):
        """
        Initialize a medieval-themed label.

        Args:
            master: Parent widget
            text: Label text
            style: Label style ('normal', 'title', 'subtitle', 'dim')
        """
        font_styles = {
            'normal': ('Arial', 14, 'normal'),
            'title': ('Arial', 24, 'bold'),
            'subtitle': ('Arial', 18, 'bold'),
            'dim': ('Arial', 12, 'normal'),
        }

        text_colors = {
            'normal': MEDIEVAL_COLORS['text_light'],
            'title': MEDIEVAL_COLORS['accent_gold'],
            'subtitle': MEDIEVAL_COLORS['accent_gold'],
            'dim': MEDIEVAL_COLORS['text_dim'],
        }

        font = font_styles.get(style, font_styles['normal'])
        text_color = text_colors.get(style, MEDIEVAL_COLORS['text_light'])

        super().__init__(master,
                         text=text,
                         font=font,
                         text_color=text_color,
                         **kwargs)


class MedievalFrame(ctk.CTkFrame):
    """
    Medieval-themed frame with ornate borders.
    """

    def __init__(self, master, **kwargs):
        """Initialize a medieval-themed frame."""
        super().__init__(master,
                         fg_color=MEDIEVAL_COLORS['bg_light'],
                         border_width=2,
                         border_color=MEDIEVAL_COLORS['border_gold'],
                         corner_radius=8,
                         **kwargs)


class MedievalScrollableFrame(ctk.CTkScrollableFrame):
    """
    Medieval-themed scrollable frame for displaying lists.
    """

    def __init__(self, master, **kwargs):
        """Initialize a medieval-themed scrollable frame."""
        super().__init__(master,
                         fg_color=MEDIEVAL_COLORS['bg_light'],
                         **kwargs)


class DialogBox(ctk.CTkToplevel):
    """
    Base class for dialog boxes in the medieval theme.
    """

    def __init__(self,
                 title: str = "Dialog",
                 message: str = "",
                 buttons: Optional[List[str]] = None,
                 callback: Optional[Callable] = None):
        """
        Initialize a dialog box.

        Args:
            title: Dialog title
            message: Dialog message
            buttons: List of button labels
            callback: Callback function receiving button choice
        """
        super().__init__()
        self.title(title)
        self.geometry("500x250")
        self.configure(fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.resizable(False, False)
        self.callback = callback
        self.result = None

        # Make dialog modal
        self.attributes('-topmost', True)
        self.grab_set()

        # Title
        title_label = MedievalLabel(self,
                                    text=title,
                                    style='title',
                                    fg_color=MEDIEVAL_COLORS['bg_dark'])
        title_label.pack(pady=15, padx=10)

        # Message
        if message:  # Fixed: Only create message label if message is not empty
            message_label = MedievalLabel(self,
                                          text=message,
                                          style='normal',
                                          fg_color=MEDIEVAL_COLORS['bg_dark'])
            message_label.pack(pady=10, padx=10, fill=ctk.BOTH, expand=True)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color=MEDIEVAL_COLORS['bg_dark'])
        button_frame.pack(pady=15, padx=10, fill=ctk.X)

        if buttons is None:
            buttons = ['OK']

        for button_text in buttons:
            button = MedievalButton(
                button_frame,
                text=button_text,
                command=lambda bt=button_text: self.on_button_click(bt))
            button.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)

    def on_button_click(self, button_text: str):
        """Handle button click."""
        self.result = button_text
        if self.callback:
            self.callback(button_text)
        self.destroy()

    def get_result(self) -> Optional[str]:
        """Get the dialog result."""
        return self.result


class InventoryDialog(DialogBox):
    """
    Dialog for displaying and managing inventory items.
    """

    def __init__(self, items: List[Dict[str, Any]], title: str = "Inventory"):
        """
        Initialize inventory dialog.

        Args:
            items: List of item dictionaries with 'name', 'quantity', and 'rarity' keys
            title: Dialog title
        """
        self.items = items
        super().__init__(title=title, message="",
                         buttons=['Close'])  # Fixed: Pass empty message

        self.geometry("600x400")

        # Items list
        if items:
            items_frame = MedievalScrollableFrame(self, height=250)
            items_frame.pack(pady=10, padx=10, fill=ctk.BOTH, expand=True)

            for item in items:
                self.create_item_widget(items_frame, item)
        else:
            empty_label = MedievalLabel(self,
                                        text="Inventory is empty",
                                        style='dim')
            empty_label.pack(pady=20)

    def create_item_widget(self, parent: Any, item: Dict[str, Any]):
        """Create a widget for an inventory item."""
        item_frame = ctk.CTkFrame(parent, fg_color=MEDIEVAL_COLORS['bg_dark'])
        item_frame.pack(fill=ctk.X, padx=5, pady=5)

        name = item.get('name', 'Unknown')
        quantity = item.get('quantity', 1)
        rarity = item.get('rarity', 'common')

        rarity_color = {
            'common': MEDIEVAL_COLORS['text_light'],
            'uncommon': '#92D050',
            'rare': '#4472C4',
            'epic': '#7030A0',
            'legendary': '#FFD700',
        }.get(rarity, MEDIEVAL_COLORS['text_light'])

        item_label = ctk.CTkLabel(item_frame,
                                  text=f"{name} x{quantity}",
                                  font=('Arial', 12),
                                  text_color=rarity_color)
        item_label.pack(side=ctk.LEFT, padx=10, pady=5)


class MessageBox(DialogBox):
    """Simple message box for displaying information."""

    def __init__(self, title: str, message: str):
        """
        Initialize a message box.

        Args:
            title: Message box title
            message: Message to display
        """
        super().__init__(title=title, message=message, buttons=['OK'])


class ConfirmationBox(DialogBox):
    """Confirmation dialog for yes/no choices."""

    def __init__(self,
                 title: str,
                 message: str,
                 callback: Optional[Callable] = None):
        """
        Initialize a confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message
            callback: Callback function receiving 'Yes' or 'No'
        """
        super().__init__(title=title,
                         message=message,
                         buttons=['Yes', 'No'],
                         callback=callback)


class TextInputDialog(ctk.CTkToplevel):
    """Dialog for text input."""

    def __init__(self,
                 title: str = "Input",
                 prompt: str = "Enter text:",
                 callback: Optional[Callable] = None):
        """
        Initialize text input dialog.

        Args:
            title: Dialog title
            prompt: Prompt text
            callback: Callback function receiving input text
        """
        super().__init__()
        self.title(title)
        self.geometry("400x200")
        self.configure(fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.resizable(False, False)
        self.callback = callback
        self.result = None

        self.attributes('-topmost', True)
        self.grab_set()

        # Prompt label
        prompt_label = MedievalLabel(self, text=prompt, style='normal')
        prompt_label.pack(pady=15, padx=10)

        # Input field
        self.input_field = ctk.CTkEntry(
            self,
            fg_color=MEDIEVAL_COLORS['bg_light'],
            border_color=MEDIEVAL_COLORS['border_gold'],
            border_width=2,
            text_color=MEDIEVAL_COLORS['text_light'],
            font=('Arial', 12))
        self.input_field.pack(pady=10, padx=10, fill=ctk.X)

        # Button frame
        button_frame = ctk.CTkFrame(self, fg_color=MEDIEVAL_COLORS['bg_dark'])
        button_frame.pack(pady=15, padx=10, fill=ctk.X)

        ok_button = MedievalButton(button_frame, text="OK", command=self.on_ok)
        ok_button.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)

        cancel_button = MedievalButton(button_frame,
                                       text="Cancel",
                                       command=self.on_cancel)
        cancel_button.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)

    def on_ok(self):
        """Handle OK button click."""
        self.result = self.input_field.get()
        if self.callback:
            self.callback(self.result)
        self.destroy()

    def on_cancel(self):
        """Handle Cancel button click."""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[str]:
        """Get the input result."""
        return self.result


# ============================================
# NEW GUI COMPONENTS FOR GAME WINDOW
# ============================================

class GameWindow(ctk.CTk):
    """
    Main game window with sidebar, content area, message panel, and status bar.
    """
    
    def __init__(self, title: str = "Our Legacy", width: int = 1200, height: int = 800):
        """Initialize the game window."""
        super().__init__()

        self.title(title)
        self.geometry(f"{width}x{height}")
        self.minsize(1000, 700)

        # Configure color scheme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.configure(fg_color=MEDIEVAL_COLORS['bg_dark'])

        # Game reference
        self.game = None
        
        # Current view
        self.current_view = None
        
        # Message log
        self.message_log: List[str] = []
        
        # Callback for menu commands
        self.menu_callback: Optional[Callable] = None
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main UI layout."""
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.main_container.pack(fill=ctk.BOTH, expand=True)
        
        # Left sidebar (navigation)
        self.sidebar = MedievalFrame(self.main_container, width=200)
        self.sidebar.pack(side=ctk.LEFT, fill=ctk.Y, padx=(0, 5))
        self.sidebar.pack_propagate(False)
        
        # Main content area
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.content_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True)
        
        # Status bar at bottom
        self.status_bar = MedievalFrame(self.content_frame, height=60)
        self.status_bar.pack(side=ctk.BOTTOM, fill=ctk.X, pady=(5, 0))
        
        # Message panel
        self.message_panel = MedievalScrollableFrame(self.content_frame, height=150)
        self.message_panel.pack(side=ctk.BOTTOM, fill=ctk.X, pady=(5, 0))
        
        # Game content area (middle)
        self.game_content = MedievalFrame(self.content_frame)
        self.game_content.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)
        
        # Setup sidebar
        self.setup_sidebar()
        
        # Setup status bar
        self.setup_status_bar()
        
    def setup_sidebar(self):
        """Setup the sidebar navigation."""
        # Title
        title_label = MedievalLabel(self.sidebar, text="OUR LEGACY", style='title')
        title_label.pack(pady=20, padx=10)
        
        # Navigation buttons
        self.nav_buttons = {}
        
        nav_items = [
            ("Explore", self.on_explore),
            ("Character", self.on_character),
            ("Travel", self.on_travel),
            ("Inventory", self.on_inventory),
            ("Missions", self.on_missions),
            ("Boss", self.on_boss),
            ("Tavern", self.on_tavern),
            ("Shop", self.on_shop),
            ("Alchemy", self.on_alchemy),
            ("Market", self.on_market),
            ("Rest", self.on_rest),
            ("Companions", self.on_companions),
            ("Dungeons", self.on_dungeons),
            ("Challenges", self.on_challenges),
            ("Settings", self.on_settings),
        ]
        
        for label, command in nav_items:
            btn = MedievalButton(self.sidebar, text=label, command=command, size='small')
            btn.pack(pady=3, padx=10, fill=ctk.X)
            self.nav_buttons[label] = btn
            
        # Land-specific buttons (shown when in your_land)
        self.land_buttons = []
        land_items = [
            ("Pet Shop", self.on_pet_shop),
            ("Furnish Home", self.on_furnish_home),
            ("Build", self.on_build),
            ("Farm", self.on_farm),
            ("Training", self.on_training),
        ]
        
        for label, command in land_items:
            btn = MedievalButton(self.sidebar, text=label, command=command, size='small')
            btn.pack(pady=3, padx=10, fill=ctk.X)
            self.land_buttons.append(btn)
            
        # Save/Load/Quit
        ctk.CTkLabel(self.sidebar, text="", height=20).pack()
        
        self.save_btn = MedievalButton(self.sidebar, text="Save Game", command=self.on_save, size='small')
        self.save_btn.pack(pady=3, padx=10, fill=ctk.X)
        
        self.load_btn = MedievalButton(self.sidebar, text="Load Game", command=self.on_load, size='small')
        self.load_btn.pack(pady=3, padx=10, fill=ctk.X)
        
        self.claim_btn = MedievalButton(self.sidebar, text="Claim Rewards", command=self.on_claim, size='small')
        self.claim_btn.pack(pady=3, padx=10, fill=ctk.X)
        
        ctk.CTkLabel(self.sidebar, text="", height=20).pack()
        
        self.quit_btn = MedievalButton(self.sidebar, text="Quit", command=self.on_quit, size='small')
        self.quit_btn.pack(pady=3, padx=10, fill=ctk.X)
        
    def setup_status_bar(self):
        """Setup the status bar showing player stats."""
        # Player info will be updated when game starts
        self.status_labels = {}
        
        # HP
        hp_frame = ctk.CTkFrame(self.status_bar, fg_color='transparent')
        hp_frame.pack(side=ctk.LEFT, padx=10, pady=5)
        
        self.hp_label = MedievalLabel(hp_frame, text="HP: --/--", style='normal')
        self.hp_label.pack()
        
        # MP
        mp_frame = ctk.CTkFrame(self.status_bar, fg_color='transparent')
        mp_frame.pack(side=ctk.LEFT, padx=10, pady=5)
        
        self.mp_label = MedievalLabel(mp_frame, text="MP: --/--", style='normal')
        self.mp_label.pack()
        
        # Level
        lvl_frame = ctk.CTkFrame(self.status_bar, fg_color='transparent')
        lvl_frame.pack(side=ctk.LEFT, padx=10, pady=5)
        
        self.level_label = MedievalLabel(lvl_frame, text="Level: --", style='normal')
        self.level_label.pack()
        
        # Gold
        gold_frame = ctk.CTkFrame(self.status_bar, fg_color='transparent')
        gold_frame.pack(side=ctk.LEFT, padx=10, pady=5)
        
        self.gold_label = MedievalLabel(gold_frame, text="Gold: --", style='normal')
        self.gold_label.pack()
        
        # Location
        loc_frame = ctk.CTkFrame(self.status_bar, fg_color='transparent')
        loc_frame.pack(side=ctk.LEFT, padx=10, pady=5)
        
        self.location_label = MedievalLabel(loc_frame, text="Location: --", style='normal')
        self.location_label.pack()
        
        # Time
        time_frame = ctk.CTkFrame(self.status_bar, fg_color='transparent')
        time_frame.pack(side=ctk.RIGHT, padx=10, pady=5)
        
        self.time_label = MedievalLabel(time_frame, text="Day --, --:--", style='normal')
        self.time_label.pack()
        
    def update_status(self, player):
        """Update the status bar with player info."""
        if not player:
            return
            
        self.hp_label.configure(text=f"HP: {player.hp}/{player.max_hp}")
        self.mp_label.configure(text=f"MP: {player.mp}/{player.max_mp}")
        self.level_label.configure(text=f"Level: {player.level}")
        self.gold_label.configure(text=f"Gold: {player.gold}")
        
        # Get area name
        if self.game:
            area_data = self.game.areas_data.get(player.current_area, {})
            area_name = area_data.get('name', player.current_area)
            self.location_label.configure(text=f"Location: {area_name}")
        
        # Time
        display_hour = int(player.hour)
        display_minute = int((player.hour - display_hour) * 60)
        self.time_label.configure(text=f"Day {player.day}, {display_hour:02d}:{display_minute:02d}")
        
    def clear_content(self):
        """Clear the game content area."""
        for widget in self.game_content.winfo_children():
            widget.destroy()
            
    def add_message(self, message: str, color: str = None):
        """Add a message to the message panel."""
        if color is None:
            color = MEDIEVAL_COLORS['text_light']
            
        msg_label = ctk.CTkLabel(self.message_panel, text=message, text_color=color, anchor='w', justify='left')
        msg_label.pack(fill=ctk.X, padx=5, pady=2)
        
        self.message_log.append(message)
        
        # Auto-scroll to bottom
        self.message_panel._parent_canvas.yview_moveto(1.0)
        
    def clear_messages(self):
        """Clear all messages from the panel."""
        for widget in self.message_panel.winfo_children():
            widget.destroy()
        self.message_log.clear()
        
    # Navigation callbacks
    def on_explore(self):
        if self.menu_callback:
            self.menu_callback("explore")
            
    def on_character(self):
        if self.menu_callback:
            self.menu_callback("character")
            
    def on_travel(self):
        if self.menu_callback:
            self.menu_callback("travel")
            
    def on_inventory(self):
        if self.menu_callback:
            self.menu_callback("inventory")
            
    def on_missions(self):
        if self.menu_callback:
            self.menu_callback("missions")
            
    def on_boss(self):
        if self.menu_callback:
            self.menu_callback("boss")
            
    def on_tavern(self):
        if self.menu_callback:
            self.menu_callback("tavern")
            
    def on_shop(self):
        if self.menu_callback:
            self.menu_callback("shop")
            
    def on_alchemy(self):
        if self.menu_callback:
            self.menu_callback("alchemy")
            
    def on_market(self):
        if self.menu_callback:
            self.menu_callback("market")
            
    def on_rest(self):
        if self.menu_callback:
            self.menu_callback("rest")
            
    def on_companions(self):
        if self.menu_callback:
            self.menu_callback("companions")
            
    def on_dungeons(self):
        if self.menu_callback:
            self.menu_callback("dungeons")
            
    def on_challenges(self):
        if self.menu_callback:
            self.menu_callback("challenges")
            
    def on_settings(self):
        if self.menu_callback:
            self.menu_callback("settings")
            
    def on_pet_shop(self):
        if self.menu_callback:
            self.menu_callback("pet_shop")
            
    def on_furnish_home(self):
        if self.menu_callback:
            self.menu_callback("furnish_home")
            
    def on_build(self):
        if self.menu_callback:
            self.menu_callback("build")
            
    def on_farm(self):
        if self.menu_callback:
            self.menu_callback("farm")
            
    def on_training(self):
        if self.menu_callback:
            self.menu_callback("training")
            
    def on_save(self):
        if self.menu_callback:
            self.menu_callback("save")
            
    def on_load(self):
        if self.menu_callback:
            self.menu_callback("load")
            
    def on_claim(self):
        if self.menu_callback:
            self.menu_callback("claim")
            
    def on_quit(self):
        if self.menu_callback:
            self.menu_callback("quit")
            
    def show_land_buttons(self, show: bool = True):
        """Show or hide land-specific buttons."""
        for btn in self.land_buttons:
            if show:
                btn.pack(pady=3, padx=10, fill=ctk.X)
            else:
                btn.pack_forget()


class ChoiceDialog(ctk.CTkToplevel):
    """Dialog for making choices from a list."""
    
    def __init__(self, title: str, message: str, choices: List[str], callback: Callable[[str], None] = None):
        """Initialize choice dialog."""
        super().__init__()
        self.title(title)
        self.geometry("500x400")
        self.configure(fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.resizable(False, False)
        self.callback = callback
        self.result = None
        
        self.attributes('-topmost', True)
        self.grab_set()
        
        # Title
        title_label = MedievalLabel(self, text=title, style='title')
        title_label.pack(pady=15, padx=10)
        
        # Message
        if message:
            msg_label = MedievalLabel(self, text=message, style='normal')
            msg_label.pack(pady=10, padx=10)
        
        # Choices
        self.choices = choices
        choices_frame = MedievalScrollableFrame(self, height=250)
        choices_frame.pack(pady=10, padx=10, fill=ctk.BOTH, expand=True)
        
        for i, choice in enumerate(choices, 1):
            btn = MedievalButton(
                choices_frame,
                text=f"{i}. {choice}",
                command=lambda c=choice: self.on_select(c),
                size='normal'
            )
            btn.pack(pady=5, padx=5, fill=ctk.X)
            
        # Cancel button
        cancel_btn = MedievalButton(self, text="Cancel", command=self.on_cancel, size='normal')
        cancel_btn.pack(pady=10, padx=10, fill=ctk.X)
        
    def on_select(self, choice: str):
        """Handle choice selection."""
        self.result = choice
        if self.callback:
            self.callback(choice)
        self.destroy()
        
    def on_cancel(self):
        """Handle cancel."""
        self.result = None
        self.destroy()


class InputDialog(ctk.CTkToplevel):
    """Dialog for text input with validation."""
    
    def __init__(self, title: str, prompt: str, default: str = "", callback: Callable[[str], None] = None):
        """Initialize input dialog."""
        super().__init__()
        self.title(title)
        self.geometry("450x220")
        self.configure(fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.resizable(False, False)
        self.callback = callback
        self.result = None
        
        self.attributes('-topmost', True)
        self.grab_set()
        
        # Prompt
        prompt_label = MedievalLabel(self, text=prompt, style='normal')
        prompt_label.pack(pady=15, padx=10)
        
        # Input field
        self.input_field = ctk.CTkEntry(
            self,
            fg_color=MEDIEVAL_COLORS['bg_light'],
            border_color=MEDIEVAL_COLORS['border_gold'],
            border_width=2,
            text_color=MEDIEVAL_COLORS['text_light'],
            font=('Arial', 14)
        )
        self.input_field.pack(pady=10, padx=20, fill=ctk.X)
        self.input_field.insert(0, default)
        self.input_field.focus()
        self.input_field.bind("<Return>", lambda e: self.on_ok())
        
        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color=MEDIEVAL_COLORS['bg_dark'])
        button_frame.pack(pady=15, padx=10, fill=ctk.X)
        
        ok_btn = MedievalButton(button_frame, text="OK", command=self.on_ok, size='normal')
        ok_btn.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
        cancel_btn = MedievalButton(button_frame, text="Cancel", command=self.on_cancel, size='normal')
        cancel_btn.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
    def on_ok(self):
        """Handle OK button."""
        self.result = self.input_field.get()
        if self.callback:
            self.callback(self.result)
        self.destroy()
        
    def on_cancel(self):
        """Handle cancel."""
        self.result = None
        self.destroy()


class NumberInputDialog(ctk.CTkToplevel):
    """Dialog for numeric input."""
    
    def __init__(self, title: str, prompt: str, min_val: int = 1, max_val: int = 999, default: int = 1, callback: Callable[[int], None] = None):
        """Initialize number input dialog."""
        super().__init__()
        self.title(title)
        self.geometry("400x250")
        self.configure(fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.resizable(False, False)
        self.callback = callback
        self.result = None
        self.min_val = min_val
        self.max_val = max_val
        
        self.attributes('-topmost', True)
        self.grab_set()
        
        # Prompt
        prompt_label = MedievalLabel(self, text=prompt, style='normal')
        prompt_label.pack(pady=15, padx=10)
        
        # Number input with spinbox
        self.spinbox = ctk.CTkSlider(self, from_=min_val, to=max_val, number_of_steps=max_val-min_val)
        self.spinbox.pack(pady=10, padx=20, fill=ctk.X)
        self.spinbox.set(default)
        
        self.value_label = MedievalLabel(self, text=str(default), style='subtitle')
        self.value_label.pack(pady=5)
        
        self.spinbox.configure(command=lambda v: self.value_label.configure(text=str(int(v))))
        
        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color=MEDIEVAL_COLORS['bg_dark'])
        button_frame.pack(pady=15, padx=10, fill=ctk.X)
        
        ok_btn = MedievalButton(button_frame, text="OK", command=self.on_ok, size='normal')
        ok_btn.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
        cancel_btn = MedievalButton(button_frame, text="Cancel", command=self.on_cancel, size='normal')
        cancel_btn.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
        
    def on_ok(self):
        """Handle OK button."""
        self.result = int(self.spinbox.get())
        if self.callback:
            self.callback(self.result)
        self.destroy()
        
    def on_cancel(self):
        """Handle cancel."""
        self.result = None
        self.destroy()


# ============================================
# GAME VIEW CLASSES
# ============================================

class BaseGameView:
    """Base class for game views."""
    
    def __init__(self, game_window: GameWindow, game):
        self.game_window = game_window
        self.game = game
        
    def show(self):
        """Show this view."""
        self.game_window.clear_content()
        
    def update(self):
        """Update the view."""
        pass


class WelcomeView(BaseGameView):
    """Welcome screen view."""
    
    def show(self):
        """Show welcome screen."""
        super().show()
        
        content = self.game_window.game_content
        
        # Title
        title = MedievalLabel(content, text="OUR LEGACY", style='title')
        title.pack(pady=30)
        
        subtitle = MedievalLabel(content, text="A Medieval Fantasy RPG", style='subtitle')
        subtitle.pack(pady=10)
        
        # Separator
        ctk.CTkLabel(content, text="").pack(pady=20)
        
        # Menu buttons
        new_game_btn = MedievalButton(content, text="New Game", command=self.on_new_game, size='large')
        new_game_btn.pack(pady=10, padx=50, fill=ctk.X)
        
        load_game_btn = MedievalButton(content, text="Load Game", command=self.on_load_game, size='large')
        load_game_btn.pack(pady=10, padx=50, fill=ctk.X)
        
        settings_btn = MedievalButton(content, text="Settings", command=self.on_settings, size='large')
        settings_btn.pack(pady=10, padx=50, fill=ctk.X)
        
        quit_btn = MedievalButton(content, text="Quit", command=self.on_quit, size='large')
        quit_btn.pack(pady=10, padx=50, fill=ctk.X)
        
    def on_new_game(self):
        """Handle new game."""
        if self.game:
            self.game.create_character()
            self.game_window.update_status(self.game.player)
            self.game_window.show_land_buttons(self.game.current_area == "your_land")
            
    def on_load_game(self):
        """Handle load game."""
        if self.game:
            self.game.load_game()
            if self.game.player:
                self.game_window.update_status(self.game.player)
                self.game_window.show_land_buttons(self.game.current_area == "your_land")
                
    def on_settings(self):
        """Handle settings."""
        pass
        
    def on_quit(self):
        """Handle quit."""
        self.game.quit_game()


class CharacterView(BaseGameView):
    """Character display view."""
    
    def show(self):
        """Show character stats."""
        super().show()
        
        content = self.game_window.game_content
        
        if not self.game.player:
            MedievalLabel(content, text="No character created", style='normal').pack(pady=20)
            return
            
        player = self.game.player
        
        # Character name and class
        MedievalLabel(content, text=f"{player.name} - {player.character_class}", style='title').pack(pady=20)
        
        # Stats frame
        stats_frame = MedievalFrame(content)
        stats_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=True)
        
        # Level and EXP
        MedievalLabel(stats_frame, text=f"Level: {player.level}", style='normal').pack(pady=5, padx=10, anchor='w')
        MedievalLabel(stats_frame, text=f"Experience: {player.experience}/{player.exp_to_next_level}", style='normal').pack(pady=5, padx=10, anchor='w')
        
        # HP and MP
        MedievalLabel(stats_frame, text=f"HP: {player.hp}/{player.max_hp}", style='normal').pack(pady=5, padx=10, anchor='w')
        MedievalLabel(stats_frame, text=f"MP: {player.mp}/{player.max_mp}", style='normal').pack(pady=5, padx=10, anchor='w')
        
        # Stats
        MedievalLabel(stats_frame, text=f"Attack: {player.attack}", style='normal').pack(pady=5, padx=10, anchor='w')
        MedievalLabel(stats_frame, text=f"Defense: {player.defense}", style='normal').pack(pady=5, padx=10, anchor='w')
        MedievalLabel(stats_frame, text=f"Speed: {player.speed}", style='normal').pack(pady=5, padx=10, anchor='w')
        
        # Gold
        MedievalLabel(stats_frame, text=f"Gold: {player.gold}", style='normal').pack(pady=5, padx=10, anchor='w')
        
        # Equipment
        MedievalLabel(content, text="Equipment", style='subtitle').pack(pady=10)
        
        equip_frame = MedievalFrame(content)
        equip_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=True)
        
        for slot, item in player.equipment.items():
            if item:
                MedievalLabel(equip_frame, text=f"{slot.title()}: {item}", style='normal').pack(pady=2, padx=10, anchor='w')


class InventoryView(BaseGameView):
    """Inventory view."""
    
    def show(self):
        """Show inventory."""
        super().show()
        
        content = self.game_window.game_content
        
        if not self.game.player:
            MedievalLabel(content, text="No character created", style='normal').pack(pady=20)
            return
            
        player = self.game.player
        
        # Title
        MedievalLabel(content, text="Inventory", style='title').pack(pady=20)
        MedievalLabel(content, text=f"Gold: {player.gold}", style='normal').pack(pady=5)
        
        if not player.inventory:
            MedievalLabel(content, text="Inventory is empty", style='dim').pack(pady=20)
            return
            
        # Group items by type
        items_by_type = {}
        for item in player.inventory:
            item_type = self.game.items_data.get(item, {}).get("type", "unknown")
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)
            
        # Display items
        for item_type, items in items_by_type.items():
            MedievalLabel(content, text=item_type.title(), style='subtitle').pack(pady=10, padx=20, anchor='w')
            
            items_frame = MedievalScrollableFrame(content, height=150)
            items_frame.pack(pady=5, padx=20, fill=ctk.BOTH, expand=True)
            
            for item in items:
                item_data = self.game.items_data.get(item, {})
                rarity = item_data.get('rarity', 'common')
                color = RARITY_COLORS.get(rarity, MEDIEVAL_COLORS['text_light'])
                
                item_frame = ctk.CTkFrame(items_frame, fg_color=MEDIEVAL_COLORS['bg_dark'])
                item_frame.pack(fill=ctk.X, padx=5, pady=2)
                
                ctk.CTkLabel(item_frame, text=item, text_color=color).pack(side=ctk.LEFT, padx=10, pady=5)
                
                if item_data.get('description'):
                    ctk.CTkLabel(item_frame, text=item_data.get('description', ''), text_color=MEDIEVAL_COLORS['text_dim'], font=('Arial', 10)).pack(side=ctk.RIGHT, padx=10, pady=5)


class MissionsView(BaseGameView):
    """Missions view."""
    
    def show(self):
        """Show missions."""
        super().show()
        
        content = self.game_window.game_content
        
        if not self.game.player:
            MedievalLabel(content, text="No character created", style='normal').pack(pady=20)
            return
            
        # Title
        MedievalLabel(content, text="Missions", style='title').pack(pady=20)
        
        # Active missions
        active_missions = [
            mid for mid in self.game.mission_progress.keys()
            if not self.game.mission_progress[mid].get('completed', False)
        ]
        
        if active_missions:
            MedievalLabel(content, text="Active Missions", style='subtitle').pack(pady=10)
            
            missions_frame = MedievalScrollableFrame(content, height=300)
            missions_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=True)
            
            for mid in active_missions:
                mission = self.game.missions_data.get(mid, {})
                progress = self.game.mission_progress[mid]
                
                mission_frame = MedievalFrame(missions_frame)
                mission_frame.pack(fill=ctk.X, pady=5, padx=5)
                
                MedievalLabel(mission_frame, text=mission.get('name', 'Unknown'), style='normal').pack(pady=5, padx=10, anchor='w')
                MedievalLabel(mission_frame, text=mission.get('description', ''), style='dim').pack(pady=2, padx=10, anchor='w')
                
                if progress['type'] == 'kill':
                    MedievalLabel(mission_frame, text=f"Progress: {progress['current_count']}/{progress['target_count']}", style='normal').pack(pady=2, padx=10, anchor='w')
        else:
            MedievalLabel(content, text="No active missions", style='dim').pack(pady=20)
            
        # Available missions button
        available_btn = MedievalButton(content, text="View Available Missions", command=self.show_available_missions, size='normal')
        available_btn.pack(pady=10)
        
    def show_available_missions(self):
        """Show available missions dialog."""
        available = [
            mid for mid in self.game.missions_data.keys()
            if mid not in self.game.mission_progress
            and mid not in self.game.completed_missions
        ]
        
        if not available:
            MessageBox("Missions", "No new missions available.")
            return
            
        choices = [self.game.missions_data.get(mid, {}).get('name', mid) for mid in available[:20]]
        
        def on_select(choice):
            idx = choices.index(choice)
            mission_id = available[idx]
            self.game.accept_mission(mission_id)
            self.show()  # Refresh view
            
        ChoiceDialog("Select Mission", "Choose a mission to accept:", choices, on_select)


class ShopView(BaseGameView):
    """Shop view."""
    
    def show(self):
        """Show shop."""
        super().show()
        
        content = self.game_window.game_content
        
        if not self.game.player:
            MedievalLabel(content, text="No character created", style='normal').pack(pady=20)
            return
            
        area_data = self.game.areas_data.get(self.game.current_area, {})
        area_shops = area_data.get("shops", [])
        
        # Add housing shop if in your_land
        available_shops = list(area_shops)
        if self.game.current_area == "your_land":
            available_shops.append("housing_shop")
            
        if not available_shops:
            MedievalLabel(content, text="No shops in this area", style='normal').pack(pady=20)
            return
            
        # Title
        MedievalLabel(content, text=f"Shops in {area_data.get('name', 'Unknown')}", style='title').pack(pady=20)
        MedievalLabel(content, text=f"Your Gold: {self.game.player.gold}", style='normal').pack(pady=5)
        
        # Shop list
        shops_frame = MedievalScrollableFrame(content, height=400)
        shops_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=True)
        
        for shop_id in available_shops:
            if shop_id == "housing_shop":
                shop_name = "Housing Shop"
            else:
                shop_data = self.game.shops_data.get(shop_id, {})
                shop_name = shop_data.get("name", shop_id.replace("_", " ").title())
                
            btn = MedievalButton(shops_frame, text=shop_name, command=lambda s=shop_id: self.visit_shop(s), size='normal')
            btn.pack(pady=5, padx=5, fill=ctk.X)
            
    def visit_shop(self, shop_id: str):
        """Visit a specific shop."""
        if shop_id == "housing_shop":
            self.game._visit_housing_shop_inline()
        else:
            from utilities.shop import visit_specific_shop
            visit_specific_shop(self.game, shop_id)


class BattleView(BaseGameView):
    """Battle view."""
    
    def show(self):
        """Show battle."""
        super().show()
        
        content = self.game_window.game_content
        
        MedievalLabel(content, text="Battle", style='title').pack(pady=20)
        MedievalLabel(content, text="Battle takes place in the game content area", style='dim').pack(pady=20)


class ExploreView(BaseGameView):
    """Explore view."""
    
    def show(self):
        """Show explore."""
        super().show()
        
        content = self.game_window.game_content
        
        if not self.game.player:
            MedievalLabel(content, text="No character created", style='normal').pack(pady=20)
            return
            
        area_data = self.game.areas_data.get(self.game.current_area, {})
        area_name = area_data.get("name", "Unknown Area")
        
        # Title
        MedievalLabel(content, text=f"Exploring: {area_name}", style='title').pack(pady=20)
        
        # Description
        MedievalLabel(content, text=area_data.get("description", ""), style='normal').pack(pady=10, padx=20)
        
        # Explore button
        explore_btn = MedievalButton(content, text="Explore Area", command=self.do_explore, size='large')
        explore_btn.pack(pady=20)
        
        # Enemy info
        possible_enemies = area_data.get("possible_enemies", [])
        if possible_enemies:
            MedievalLabel(content, text="Possible Enemies:", style='subtitle').pack(pady=10)
            
            enemies_frame = MedievalScrollableFrame(content, height=150)
            enemies_frame.pack(pady=10, padx=20, fill=ctk.BOTH, expand=True)
            
            for enemy_name in possible_enemies:
                enemy_data = self.game.enemies_data.get(enemy_name, {})
                MedievalLabel(enemies_frame, text=enemy_data.get('name', enemy_name), style='normal').pack(pady=2, padx=10, anchor='w')
                
    def do_explore(self):
        """Perform exploration."""
        self.game.explore()
        self.game_window.update_status(self.game.player)


# ============================================
# CLI-compatible functions (moved from UI.py)
# ============================================

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GOLD = '\033[93m'
    ORANGE = '\033[38;5;208m'
    PURPLE = '\033[95m'
    DARK_GRAY = '\033[90m'
    LIGHT_GRAY = '\033[37m'
    GRAY = '\033[90m'

    # Rarity colors for items
    COMMON = '\033[37m'
    UNCOMMON = '\033[92m'
    RARE = '\033[94m'
    EPIC = '\033[95m'
    LEGENDARY = '\033[93m'

    @staticmethod
    def _color(code: str) -> str:
        return code

    @classmethod
    def wrap(cls, text: str, color_code: str) -> str:
        return f"{color_code}{text}{cls.END}"


def clear_screen():
    """Clear the terminal screen."""
    import os
    import time
    time.sleep(0.1)
    command = 'cls' if os.name == 'nt' else 'clear'
    os.system(command)


def create_progress_bar(current: int,
                        maximum: int,
                        width: int = 20,
                        color: str = Colors.GREEN) -> str:
    """Create a visual progress bar."""
    if maximum <= 0:
        return "[" + " " * width + "]"
    filled_width = int((current / maximum) * width)
    filled = "█" * filled_width
    empty = "░" * (width - filled_width)
    percentage = (current / maximum) * 100
    return f"[{Colors.wrap(filled, color)}{empty}] {percentage:.1f}%"


def create_separator(char: str = "=", length: int = 60) -> str:
    """Create a visual separator line."""
    return char * length


def create_section_header(title: str, char: str = "=", width: int = 60) -> str:
    """Create a decorative section header."""
    padding = (width - len(title) - 2) // 2
    header_text = f"{char * padding} {title} {char * padding}"
    return Colors.wrap(header_text, f"{Colors.CYAN}{Colors.BOLD}")


# ============================================
# GUI MODE FUNCTIONS
# ============================================

# GUI mode flag - set to True to use GUI dialogs instead of CLI
GUI_MODE = False

# Global reference to the main game window
_main_window: Optional[GameWindow] = None


def set_main_window(window):
    """Set the main game window reference for GUI dialogs."""
    global _main_window
    _main_window = window


def set_gui_mode(enabled: bool):
    """Enable or disable GUI mode."""
    global GUI_MODE
    GUI_MODE = enabled


def is_gui_mode() -> bool:
    """Check if GUI mode is enabled."""
    return GUI_MODE


def show_gui(message: str, title: str = "Message", dialog_type: str = "message"):
    """
    Custom module for displaying output - either in GUI dialogs or console.
    """
    if GUI_MODE and _main_window is not None:
        # Add to message panel
        _main_window.add_message(message)
        return None
    else:
        # Fall back to console output
        print(message)
        return None


def show_message_gui(title: str, message: str):
    """Show a message dialog."""
    if GUI_MODE and _main_window is not None:
        _main_window.add_message(f"[{title}] {message}")
    else:
        print(f"[{title}] {message}")


def show_choice_gui(title: str, message: str, choices: List[str], callback: Callable[[str], None] = None) -> Optional[str]:
    """
    Show a choice dialog and return the selected option.
    """
    if GUI_MODE and _main_window is not None:
        # Use GUI dialog
        dialog = ChoiceDialog(title, message, choices, callback)
        return None
    else:
        # Console fallback
        for i, choice in enumerate(choices, 1):
            print(f"{i}. {choice}")
        return None


def show_input_gui(title: str, prompt: str, callback: Callable[[str], None] = None) -> Optional[str]:
    """
    Show an input dialog and return the user's input.
    """
    if GUI_MODE and _main_window is not None:
        dialog = InputDialog(title, prompt, callback=callback)
        return None
    else:
        # Console fallback
        return input(prompt)


def show_confirmation_gui(title: str, message: str, callback: Callable[[bool], None] = None):
    """Show a confirmation dialog."""
    if GUI_MODE and _main_window is not None:
        def on_result(result):
