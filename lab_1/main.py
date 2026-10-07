from viewmodel.color_viewmodel import ColorViewModel
from view.app_window import AppWindow

if __name__ == "__main__":
    vm = ColorViewModel("D65")
    AppWindow(vm).mainloop()