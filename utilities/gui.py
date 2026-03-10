"""
Medieval-themed GUI for Our Legacy RPG using customtkinter.
Provides a modern interface with a dark fantasy aesthetic.
"""

import customtkinter as ctk
from typing import Callable, Optional, List, Dict, Any
import tkinter as tk


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
}


class MedievalApp(ctk.CTk):
    """
    Main medieval-themed application window for Our Legacy RPG.
    Serves as the base window for all GUI interactions.
    """

    def __init__(self, title: str = "Our Legacy", width: int = 1000, height: int = 700):
        """
        Initialize the main application window.

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
        self.main_frame = None
        self.setup_main_frame()

    def setup_main_frame(self):
        """Setup the main content frame."""
        self.main_frame = ctk.CTkFrame(self, fg_color=MEDIEVAL_COLORS['bg_dark'])
        self.main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

    def clear_frame(self, frame: ctk.CTkFrame = None):
        """Clear all widgets from a frame."""
        target_frame = frame or self.main_frame
        for widget in target_frame.winfo_children():
            widget.destroy()

    def get_main_frame(self) -> ctk.CTkFrame:
        """Get the main content frame."""
        return self.main_frame


class MedievalButton(ctk.CTkButton):
    """
    Medieval-themed button with ornate styling.
    """

    def __init__(self, master, text: str = "Button", command: Callable = None,
                 size: str = "normal", **kwargs):
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
        paddings = {
            'small': 8,
            'normal': 12,
            'large': 16,
        }

        font_size = font_sizes.get(size, 14)
        padding = paddings.get(size, 12)

        super().__init__(
            master,
            text=text,
            command=command,
            fg_color=MEDIEVAL_COLORS['accent_red'],
            hover_color='#a00000',
            text_color=MEDIEVAL_COLORS['text_light'],
            font=('Arial', font_size, 'bold'),
            border_width=2,
            border_color=MEDIEVAL_COLORS['accent_gold'],
            corner_radius=8,
            **kwargs
        )


class MedievalLabel(ctk.CTkLabel):
    """
    Medieval-themed label with ornate styling.
    """

    def __init__(self, master, text: str = "Label", style: str = "normal", **kwargs):
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

        super().__init__(
            master,
            text=text,
            font=font,
            text_color=text_color,
            **kwargs
        )


class MedievalFrame(ctk.CTkFrame):
    """
    Medieval-themed frame with ornate borders.
    """

    def __init__(self, master, **kwargs):
        """Initialize a medieval-themed frame."""
        super().__init__(
            master,
            fg_color=MEDIEVAL_COLORS['bg_light'],
            border_width=2,
            border_color=MEDIEVAL_COLORS['border_gold'],
            corner_radius=8,
            **kwargs
        )


class MedievalScrollableFrame(ctk.CTkScrollableFrame):
    """
    Medieval-themed scrollable frame for displaying lists.
    """

    def __init__(self, master, **kwargs):
        """Initialize a medieval-themed scrollable frame."""
        super().__init__(
            master,
            fg_color=MEDIEVAL_COLORS['bg_light'],
            **kwargs
        )


class DialogBox(ctk.CTkToplevel):
    """
    Base class for dialog boxes in the medieval theme.
    """

    def __init__(self, title: str = "Dialog", message: str = "",
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
        title_label = MedievalLabel(
            self,
            text=title,
            style='title',
            fg_color=MEDIEVAL_COLORS['bg_dark']
        )
        title_label.pack(pady=15, padx=10)

        # Message
        message_label = MedievalLabel(
            self,
            text=message,
            style='normal',
            fg_color=MEDIEVAL_COLORS['bg_dark']
        )
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
                command=lambda bt=button_text: self.on_button_click(bt)
            )
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
        super().__init__(title=title, buttons=['Close'])

        self.geometry("600x400")

        # Items list
        if items:
            items_frame = MedievalScrollableFrame(self, height=250)
            items_frame.pack(pady=10, padx=10, fill=ctk.BOTH, expand=True)

            for item in items:
                self.create_item_widget(items_frame, item)
        else:
            empty_label = MedievalLabel(self, text="Inventory is empty", style='dim')
            empty_label.pack(pady=20)

    def create_item_widget(self, parent: ctk.CTkFrame, item: Dict[str, Any]):
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

        item_label = ctk.CTkLabel(
            item_frame,
            text=f"{name} x{quantity}",
            font=('Arial', 12),
            text_color=rarity_color
        )
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

    def __init__(self, title: str, message: str, callback: Optional[Callable] = None):
        """
        Initialize a confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message
            callback: Callback function receiving 'Yes' or 'No'
        """
        super().__init__(title=title, message=message, buttons=['Yes', 'No'], callback=callback)


class TextInputDialog(ctk.CTkToplevel):
    """Dialog for text input."""

    def __init__(self, title: str = "Input", prompt: str = "Enter text:",
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
            font=('Arial', 12)
        )
        self.input_field.pack(pady=10, padx=10, fill=ctk.X)

        # Button frame
        button_frame = ctk.CTkFrame(self, fg_color=MEDIEVAL_COLORS['bg_dark'])
        button_frame.pack(pady=15, padx=10, fill=ctk.X)

        ok_button = MedievalButton(
            button_frame,
            text="OK",
            command=self.on_ok
        )
        ok_button.pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)

        cancel_button = MedievalButton(
            button_frame,
            text="Cancel",
            command=self.on_cancel
        )
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
