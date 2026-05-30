import webview

if __name__ == '__main__':
    webview.create_window(
        title='Smart Plate',
        url='http://localhost:3000', 
        width=1280,
        height=800,
        background_color='#121212' 
    )
    webview.start()
    