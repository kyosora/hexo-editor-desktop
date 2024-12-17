import sys
from pathlib import Path
import yaml
from datetime import datetime

from PySide6.QtGui import QShortcut, QKeySequence, QColor
from PySide6.QtWidgets import (QDialog, QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLineEdit, QTextEdit, QPushButton,
                               QLabel, QListWidget, QFileDialog, QMessageBox,
                               QProgressBar, QGridLayout, QSplitter,
                               QGroupBox, QTreeWidget, QInputDialog, QTreeWidgetItem,
                               QCompleter, QAbstractItemView,QStatusBar,QListWidgetItem
                               )
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QThread, Signal, QTimer
import json
import markdown2


class StyleManager:
    """Qt樣式管理器"""

    def __init__(self):
        # 儲存所有樣式定義
        self.styles = {}
        # 預設樣式檔案路徑
        self.style_file = Path('styles.json')

    def load_styles(self):
        """從JSON檔載入樣式定義"""
        try:
            if self.style_file.exists():
                with open(self.style_file, 'r', encoding='utf-8') as f:
                    self.styles = json.load(f)
        except Exception as e:
            print(f"載入樣式檔案時發生錯誤: {str(e)}")

    def save_styles(self):
        """儲存樣式定義到JSON檔"""
        try:
            with open(self.style_file, 'w', encoding='utf-8') as f:
                json.dump(self.styles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"儲存樣式檔案時發生錯誤: {str(e)}")

    def add_style(self, name: str, style: str):
        """新增樣式定義"""
        self.styles[name] = style
        self.save_styles()

    def get_style(self, name: str) -> str:
        """取得指定樣式"""
        return self.styles.get(name, '')

    def apply_global_style(self, app: QApplication):
        """套用全域樣式"""
        # 合併所有樣式
        full_style = '\n'.join(self.styles.values())
        app.setStyleSheet(full_style)

    def apply_widget_style(self, widget, style_name: str):
        """套用樣式到特定元件"""
        if style := self.get_style(style_name):
            widget.setStyleSheet(style)

    def apply_combined_styles(self, widget, style_names: list):
        """套用多個樣式到元件"""
        combined_style = '\n'.join(
            self.get_style(name) for name in style_names
        )
        widget.setStyleSheet(combined_style)

class MarkdownEditor(QTextEdit):
    """自定義的Markdown編輯器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.WidgetWidth)

        # 設定等寬字型以便於編輯程式碼
        font = self.font()
        font.setFamily("Consolas")
        self.setFont(font)
class FileLoader(QThread):
    """
    非同步檔案載入器
    使用QThread避免在讀取大量檔案時凍結UI
    """
    finished = Signal(list)  # 完成信號，傳送文章列表
    error = Signal(str)  # 錯誤信號
    progress = Signal(int)  # 進度信號

    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def run(self):
        try:
            articles = []
            md_files = list(Path(self.directory).rglob("*.md"))
            total_files = len(md_files)

            for i, md_file in enumerate(md_files):
                try:
                    # 讀取markdown檔案
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 分割front matter和內容
                    if content.startswith('---'):
                        _, fm, _ = content.split('---', 2)
                        # 解析YAML
                        metadata = yaml.safe_load(fm)
                    else:
                        metadata = {}

                    # 取得文章資訊
                    info = {
                        'title': metadata.get('title', '未命名'),
                        'date': metadata.get('date', '無日期'),
                        'path': str(md_file),
                        'categories': metadata.get('categories', []),
                        'tags': metadata.get('tags', [])
                    }
                    articles.append(info)

                    # 更新進度
                    self.progress.emit(int((i + 1) / total_files * 100))

                except Exception as e:
                    print(f"讀取檔案 {md_file} 時發生錯誤: {str(e)}")

            # 依日期排序
            articles.sort(key=lambda x: str(x['date']), reverse=True)
            self.finished.emit(articles)

        except Exception as e:
            self.error.emit(f"載入文章時發生錯誤: {str(e)}")


class HexoEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HEXO文章編輯器")
        self.setGeometry(100, 100, 1200, 800)
        self.articles = []
        self.current_file = None
        self.style_manager = StyleManager()

        # 註冊樣式
        self.style_manager.add_style('material-button', '''
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
                font-weight: 500;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                transition: background-color 0.3s;
            }

            QPushButton:hover {
                background-color: #1976D2;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }

            QPushButton:pressed {
                background-color: #0D47A1;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            }

            QPushButton:disabled {
                background-color: #BDBDBD;
                color: rgba(255,255,255,0.7);
                box-shadow: none;
            }
        ''')
        self.style_manager.add_style('material-input', '''
            QLineEdit {
                background: var(--background);
                border: 1px solid var(--border);
                border-radius: 4px;
            }
        ''')

        # 建立主要widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)


        # 建立狀態列
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # 建立通知標籤
        self.notification_label = QLabel()
        self.notification_label.hide()

        # 將通知標籤加入狀態列
        self.statusBar.addPermanentWidget(self.notification_label)

        # 建立儲存快捷鍵
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_article)

        # 建立分隔器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左側面板（文章列表）
        left_panel = QWidget()
        left_panel.setFixedWidth(300)  # 固定寬度
        left_layout = QVBoxLayout(left_panel)


        # 選擇目錄按鈕
        self.select_dir_btn = QPushButton("選擇文章目錄")
        self.select_dir_btn.clicked.connect(self.select_directory)
        left_layout.addWidget(self.select_dir_btn)


        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # 搜尋框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜尋文章...")
        self.search_box.textChanged.connect(self.filter_articles)
        left_layout.addWidget(self.search_box)

        # 文章列表
        self.article_list = QListWidget()
        self.article_list.itemClicked.connect(self.load_article)
        left_layout.addWidget(self.article_list)

        # 新增文章按鈕
        self.new_article_btn = QPushButton("新增文章")
        self.new_article_btn.clicked.connect(self.new_article)
        left_layout.addWidget(self.new_article_btn)

        # 匯出按鈕
        self.export_btn = QPushButton("匯出備份")
        self.export_btn.clicked.connect(self.export_articles)
        left_layout.addWidget(self.export_btn)

        # 設定左側面板
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # 右側編輯面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)


        # YAML編輯區 - 使用較緊湊的佈局
        yaml_group = QGroupBox("文章資訊")
        yaml_layout = QGridLayout()

        # 文章資訊欄位使用較小的高度
        small_height = 25

        # 標題
        yaml_layout.addWidget(QLabel("標題："), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setFixedHeight(small_height)
        yaml_layout.addWidget(self.title_edit, 0, 1)

        # 日期
        yaml_layout.addWidget(QLabel("日期："), 1, 0)
        self.date_edit = QLineEdit()
        self.date_edit.setFixedHeight(small_height)
        self.date_edit.setPlaceholderText("YYYY-MM-DD HH:mm:ss")
        yaml_layout.addWidget(self.date_edit, 1, 1)

        # 封面圖片
        yaml_layout.addWidget(QLabel("封面："), 2, 0)
        self.cover_edit = QLineEdit()
        self.cover_edit.setFixedHeight(small_height)
        yaml_layout.addWidget(self.cover_edit, 2, 1)

        # 分類
        yaml_layout.addWidget(QLabel("分類："), 3, 0)
        self.category_edit = QLineEdit()
        self.category_edit.setFixedHeight(small_height)
        self.category_edit.setPlaceholderText("使用逗號分隔多個分類")
        yaml_layout.addWidget(self.category_edit, 3, 1)

        # 標籤
        yaml_layout.addWidget(QLabel("標籤："), 4, 0)
        self.tags_edit = QLineEdit()
        self.tags_edit.setFixedHeight(small_height)
        self.tags_edit.setPlaceholderText("使用逗號分隔多個標籤")
        yaml_layout.addWidget(self.tags_edit, 4, 1)

        # 分類管理按鈕
        category_btn = QPushButton("管理分類")
        category_btn.setFixedHeight(small_height)
        category_btn.clicked.connect(self.show_category_manager)
        yaml_layout.addWidget(category_btn, 3, 2)

        # 標籤管理按鈕
        tag_btn = QPushButton("管理標籤")
        tag_btn.setFixedHeight(small_height)
        tag_btn.clicked.connect(self.show_tag_manager)
        yaml_layout.addWidget(tag_btn, 4, 2)

        yaml_group.setLayout(yaml_layout)
        # 設定固定高度讓文章資訊區塊更緊湊
        yaml_group.setFixedHeight(200)
        right_layout.addWidget(yaml_group)

        # 建立水平分割器用於編輯和預覽
        editor_splitter = QSplitter(Qt.Horizontal)

        # Markdown編輯區
        markdown_group = QGroupBox("編輯")
        markdown_layout = QVBoxLayout()
        self.content_edit = MarkdownEditor()
        # 在 content_edit 的 textChanged 信號連接中新增 front matter 解析
        self.content_edit.textChanged.connect(self.update_preview)
        self.content_edit.textChanged.connect(self.parse_front_matter)
        markdown_layout.addWidget(self.content_edit)
        markdown_group.setLayout(markdown_layout)
        editor_splitter.addWidget(markdown_group)

        # 預覽區
        preview_group = QGroupBox("預覽")
        preview_layout = QVBoxLayout()
        self.preview_view = QWebEngineView()
        preview_layout.addWidget(self.preview_view)
        preview_group.setLayout(preview_layout)
        editor_splitter.addWidget(preview_group)

        # 設定分割器比例
        editor_splitter.setSizes([500, 500])

        # 讓編輯器區域佔據更大比例的垂直空間
        right_layout.addWidget(editor_splitter, stretch=1)

        # 儲存按鈕
        self.save_btn = QPushButton("儲存文章")
        self.save_btn.setFixedHeight(small_height)
        self.save_btn.clicked.connect(self.save_article)
        right_layout.addWidget(self.save_btn)

        # 設定右側面板
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        # 設定分隔器比例
        splitter.setSizes([300, 900])
        self.apply_styles()

    def apply_styles(self):
        """套用所有樣式"""
        # 套用到按鈕
        for button in self.findChildren(QPushButton):
            self.style_manager.apply_widget_style(button, 'material-button')

        # 套用到所有輸入框
        for input_field in self.findChildren(QLineEdit):
            self.style_manager.apply_widget_style(input_field, 'material-input')

    def parse_front_matter(self):
        """解析編輯器中的 front matter 並更新表單"""
        content = self.content_edit.toPlainText()

        # 檢查是否包含 front matter
        if content.startswith('---'):
            try:
                # 分割 front matter
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    # 解析 YAML
                    front_matter = yaml.safe_load(parts[1])

                    # 更新表單
                    if front_matter:
                        # 更新標題
                        if 'title' in front_matter:
                            self.title_edit.setText(front_matter['title'])

                        # 更新日期
                        if 'date' in front_matter:
                            self.date_edit.setText(str(front_matter['date']))

                        # 更新封面
                        if 'cover' in front_matter:
                            self.cover_edit.setText(front_matter.get('cover', ''))

                        # 更新分類
                        if 'categories' in front_matter:
                            categories = front_matter['categories']
                            if isinstance(categories, list):
                                self.category_edit.setText(', '.join(categories))
                            else:
                                self.category_edit.setText(str(categories))

                        # 更新標籤
                        if 'tags' in front_matter:
                            tags = front_matter['tags']
                            if isinstance(tags, list):
                                self.tags_edit.setText(', '.join(tags))
                            else:
                                self.tags_edit.setText(str(tags))
            except yaml.YAMLError:
                # YAML 解析錯誤時不更新表單
                pass

    def update_preview(self):
        """更新Markdown預覽"""
        content = self.content_edit.toPlainText()

        # 移除front matter
        if content.startswith('---'):
            try:
                _, content = content.split('---', 2)[2:]
            except:
                pass

        # 轉換Markdown為HTML
        html = markdown2.markdown(
            content,
            extras=[
                'fenced-code-blocks',
                'tables',
                'task-lists',
                'heading-ids',
                'code-friendly'
            ]
        )

        # 新增基本樣式
        styled_html = f'''
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif;
                    font-size: 16px;
                    line-height: 1.5;
                    word-wrap: break-word;
                    padding: 20px;
                }}
                pre {{
                    background-color: #f6f8fa;
                    border-radius: 6px;
                    padding: 16px;
                    overflow: auto;
                }}
                code {{
                    font-family: SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace;
                    font-size: 85%;
                    padding: 0.2em 0.4em;
                    background-color: #f6f8fa;
                    border-radius: 6px;
                }}
                table {{
                    border-spacing: 0;
                    border-collapse: collapse;
                    margin: 16px 0;
                }}
                table th, table td {{
                    padding: 6px 13px;
                    border: 1px solid #d0d7de;
                }}
                table tr {{
                    background-color: #ffffff;
                    border-top: 1px solid #d0d7de;
                }}
                table tr:nth-child(2n) {{
                    background-color: #f6f8fa;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
        '''

        self.preview_view.setHtml(styled_html)

    def new_article(self):
        """新增文章"""
        self.current_file = None
        self.title_edit.clear()
        self.date_edit.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.cover_edit.clear()
        self.category_edit.clear()
        self.tags_edit.clear()
        self.content_edit.clear()

    def load_article(self, item):
        """載入選中的文章"""
        # 使用過濾後的索引來獲取正確的文章
        current_row = self.article_list.row(item)
        if hasattr(self, 'filtered_indices'):
            # 如果存在過濾索引，使用它來獲取實際的文章索引
            if current_row < len(self.filtered_indices):
                article_index = self.filtered_indices[current_row]
            else:
                return
        else:
            # 如果沒有過濾，直接使用當前行作為索引
            article_index = current_row

        try:
            article = self.articles[article_index]
            self.current_file = article['path']

            with open(self.current_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分割front matter和內容
            if content.startswith('---'):
                _, fm, content = content.split('---', 2)
                # 解析YAML
                metadata = yaml.safe_load(fm)
            else:
                metadata = {}

            # 填充表單
            self.title_edit.setText(metadata.get('title', ''))
            self.date_edit.setText(str(metadata.get('date', '')))
            self.cover_edit.setText(metadata.get('cover', ''))

            # 處理分類
            categories = metadata.get('categories', [])
            if isinstance(categories, list):
                self.category_edit.setText(', '.join(categories))
            else:
                self.category_edit.setText(str(categories))

            # 處理標籤
            tags = metadata.get('tags', [])
            if isinstance(tags, list):
                self.tags_edit.setText(', '.join(tags))
            else:
                self.tags_edit.setText(str(tags))

            # 設定內容
            self.content_edit.setText(content.strip())

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入文章時發生錯誤：{str(e)}")

    def show_notification(self, message, duration=2000):
        """顯示懸浮通知"""
        self.notification_label.setText(message)
        self.notification_label.show()

        # 設定定時器在指定時間後隱藏通知
        QTimer.singleShot(duration, self.notification_label.hide)

    def save_article(self):
        """儲存文章"""
        if not self.current_file:
            # 如果是新文章，需要選擇儲存位置
            title = self.title_edit.text()
            if not title:
                QMessageBox.warning(self, "警告", "請輸入文章標題")
                return

            filename = title.replace(' ', '-') + '.md'
            self.current_file = QFileDialog.getSaveFileName(
                self,
                "儲存文章",
                filename,
                "Markdown Files (*.md)"
            )[0]

            if not self.current_file:
                return

        try:
            content = self.content_edit.toPlainText()

            # 如果內容已經包含 front matter，先移除它
            if content.startswith('---'):
                try:
                    _, _, content = content.split('---', 2)
                    content = content.strip()
                except:
                    pass

            # 建立有序的 front matter 字典
            front_matter = {}

            # 1. title (必填)
            title = self.title_edit.text()
            front_matter['title'] = title

            # 2. date (必填)
            date = self.date_edit.text()
            front_matter['date'] = date

            # 3. cover (必填，可以是空字串)
            front_matter['cover'] = self.cover_edit.text() or ''

            # 4. categories (選填)
            categories = [cat.strip() for cat in self.category_edit.text().split(',') if cat.strip()]
            if categories:
                front_matter['categories'] = categories

            # 5. tags (選填)
            tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
            if tags:
                front_matter['tags'] = tags

            # 轉換為 YAML
            yaml_content = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)

            # 組合最終內容
            final_content = f"---\n{yaml_content}---\n\n{content}"

            # 儲存檔案
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(final_content)

            # 更新文章列表中的資訊
            for i, article in enumerate(self.articles):
                if article['path'] == self.current_file:
                    # 更新文章資訊
                    self.articles[i].update({
                        'title': title,
                        'date': date,
                        'categories': categories,
                        'tags': tags
                    })
                    # 更新列表顯示
                    display_text = f"{title} ({date})"
                    self.article_list.item(i).setText(display_text)
                    break
            else:
                # 如果是新文章，新增到列表
                new_article = {
                    'title': title,
                    'date': date,
                    'path': self.current_file,
                    'categories': categories,
                    'tags': tags
                }
                self.articles.append(new_article)
                display_text = f"{title} ({date})"
                self.article_list.addItem(display_text)

            self.show_notification("✓ 文章已儲存")

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存文章時發生錯誤：{str(e)}")

    def select_directory(self):
        """選擇HEXO文章目錄"""
        directory = QFileDialog.getExistingDirectory(self, "選擇HEXO文章目錄")
        if directory:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # 建立並啟動檔案載入器
            self.loader = FileLoader(directory)
            self.loader.finished.connect(self.update_article_list)
            self.loader.error.connect(self.show_error)
            self.loader.progress.connect(self.update_progress)
            self.loader.start()

    def update_progress(self, value):
        """更新進度條"""
        self.progress_bar.setValue(value)

    def update_article_list(self, articles):
        """更新文章列表"""
        self.articles = articles
        self.article_list.clear()
        # 重設過濾索引
        if hasattr(self, 'filtered_indices'):
            delattr(self, 'filtered_indices')

        for article in articles:
            # 顯示格式: 標題 (日期)
            display_text = f"{article['title']} ({article['date']})"
            self.article_list.addItem(display_text)

        self.progress_bar.setVisible(False)

    def filter_articles(self, text):
        """過濾文章列表"""
        self.article_list.clear()
        # 建立一個過濾後的文章索引清單
        self.filtered_indices = []

        for i, article in enumerate(self.articles):
            if text.lower() in article['title'].lower():
                display_text = f"{article['title']} ({article['date']})"
                self.article_list.addItem(display_text)
                self.filtered_indices.append(i)

    def show_error(self, message):
        """顯示錯誤訊息"""
        QMessageBox.critical(self, "錯誤", message)

    def show_category_manager(self):
        """顯示分類管理視窗"""
        if not hasattr(self, 'category_manager'):
            self.category_manager = CategoryManager(self)
            # 連接信號
            self.category_manager.categories_updated.connect(self.update_category_list)
        # 更新現有分類資料
        self.category_manager.scan_articles(self.articles)
        self.category_manager.show()

    def show_tag_manager(self):
        """顯示標籤管理視窗"""
        if not hasattr(self, 'tag_manager'):
            self.tag_manager = TagManager(self)
            # 連接信號
            self.tag_manager.tags_updated.connect(self.update_tag_list)
        # 更新現有標籤資料
        self.tag_manager.scan_articles(self.articles)
        self.tag_manager.show()

    def update_category_list(self, categories):
        """更新分類下拉選單"""
        # 取得目前的分類
        current_cats = [cat.strip() for cat in self.category_edit.text().split(',') if cat.strip()]
        # 更新自動完成列表
        completer = QCompleter(categories)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.category_edit.setCompleter(completer)

    def update_tag_list(self, tags):
        """更新標籤下拉選單"""
        # 取得目前的標籤
        current_tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        # 更新自動完成列表
        completer = QCompleter(tags)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tags_edit.setCompleter(completer)

    def export_articles(self):
        """匯出所有文章"""
        # 檢查是否已選擇文章目錄
        if not hasattr(self, 'loader') or not self.loader.directory:
            QMessageBox.warning(self, "警告", "請先選擇文章目錄")
            return

        # 選擇儲存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存備份",
            "hexo_articles_backup.zip",
            "ZIP Files (*.zip)"
        )

        if not file_path:
            return

        # 顯示進度條
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 建立並啟動匯出執行緒
        self.exporter = ExportThread(self.loader.directory, file_path)
        self.exporter.finished.connect(self.export_finished)
        self.exporter.error.connect(self.show_error)
        self.exporter.progress.connect(self.update_progress)
        self.exporter.start()

    def export_finished(self):
        """匯出完成時的處理"""
        self.progress_bar.setVisible(False)
        self.show_notification("✓ 文章備份已完成")

class CategoryManager(QDialog):
    """分類管理視窗"""
    categories_updated = Signal(list)  # 分類更新信號

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分類管理")
        self.setGeometry(200, 200, 600, 400)
        self.categories = {}  # 儲存分類資料
        self.config_file = Path('category_config.json')

        self.initUI()
        self.loadConfig()

    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 分類樹狀圖
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['分類名稱', '文章數'])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.tree)

        # 按鈕列
        btn_layout = QHBoxLayout()

        select_btn = QPushButton("選擇分類")
        select_btn.clicked.connect(self.select_categories)
        btn_layout.addWidget(select_btn)

        edit_btn = QPushButton("編輯分類")
        edit_btn.clicked.connect(self.edit_category)
        btn_layout.addWidget(edit_btn)

        merge_btn = QPushButton("合併分類")
        merge_btn.clicked.connect(self.merge_categories)
        btn_layout.addWidget(merge_btn)

        delete_btn = QPushButton("刪除分類")
        delete_btn.clicked.connect(self.delete_category)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def loadConfig(self):
        """載入設定檔"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
                self.updateTree()
            except Exception as e:
                QMessageBox.warning(self, "警告", f"載入設定檔時發生錯誤：{str(e)}")

    def saveConfig(self):
        """儲存設定檔"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存設定檔時發生錯誤：{str(e)}")

    def select_categories(self):
        """開啟分類選擇對話框"""
        # 取得目前的分類
        current_categories = [cat.strip() for cat in self.parent().category_edit.text().split(',') if cat.strip()]

        # 顯示分類選擇對話框
        selector = CategorySelector(self.categories, current_categories, self)
        if selector.exec() == QDialog.Accepted:
            # 更新分類輸入框
            selected_categories = selector.get_selected_categories()
            self.parent().category_edit.setText(', '.join(selected_categories))

    def updateTree(self):
        """更新分類樹狀圖"""
        self.tree.clear()
        for main_cat, data in self.categories.items():
            item = QTreeWidgetItem([main_cat, str(data.get('count', 0))])
            self.tree.addTopLevelItem(item)
            for sub_cat, count in data.get('subcategories', {}).items():
                sub_item = QTreeWidgetItem([sub_cat, str(count)])
                item.addChild(sub_item)
        self.tree.expandAll()

    def scan_articles(self, articles):
        """掃描文章更新分類統計"""
        # 重設計數
        for cat_data in self.categories.values():
            cat_data['count'] = 0
            for sub_cat in cat_data.get('subcategories', {}):
                cat_data['subcategories'][sub_cat] = 0

        # 統計文章分類
        for article in articles:
            categories = article.get('categories', [])
            if isinstance(categories, list):
                for cat in categories:
                    if '/' in cat:  # 子分類
                        main_cat, sub_cat = cat.split('/', 1)
                        if main_cat not in self.categories:
                            self.categories[main_cat] = {'count': 0, 'subcategories': {}}
                        if sub_cat not in self.categories[main_cat]['subcategories']:
                            self.categories[main_cat]['subcategories'][sub_cat] = 0
                        self.categories[main_cat]['count'] += 1
                        self.categories[main_cat]['subcategories'][sub_cat] += 1
                    else:  # 主分類
                        if cat not in self.categories:
                            self.categories[cat] = {'count': 0, 'subcategories': {}}
                        self.categories[cat]['count'] += 1

        self.updateTree()
        self.saveConfig()
        # 發送更新信號
        all_categories = []
        for main_cat, data in self.categories.items():
            all_categories.append(main_cat)
            all_categories.extend([f"{main_cat}/{sub_cat}"
                                   for sub_cat in data.get('subcategories', {})])
        self.categories_updated.emit(all_categories)

    def add_category(self):
        """新增分類"""
        name, ok = QInputDialog.getText(self, "新增分類", "請輸入分類名稱：")
        if ok and name:
            if '/' in name:  # 子分類
                main_cat, sub_cat = name.split('/', 1)
                if main_cat not in self.categories:
                    self.categories[main_cat] = {'count': 0, 'subcategories': {}}
                self.categories[main_cat]['subcategories'][sub_cat] = 0
            else:  # 主分類
                if name not in self.categories:
                    self.categories[name] = {'count': 0, 'subcategories': {}}
            self.updateTree()
            self.saveConfig()

    def edit_category(self):
        """編輯分類"""
        item = self.tree.currentItem()
        if item:
            old_name = item.text(0)
            new_name, ok = QInputDialog.getText(
                self, "編輯分類", "請輸入新的分類名稱：",
                text=old_name
            )
            if ok and new_name and new_name != old_name:
                parent = item.parent()
                if parent:  # 子分類
                    main_cat = parent.text(0)
                    count = self.categories[main_cat]['subcategories'].pop(old_name)
                    self.categories[main_cat]['subcategories'][new_name] = count
                else:  # 主分類
                    self.categories[new_name] = self.categories.pop(old_name)
                self.updateTree()
                self.saveConfig()

    def merge_categories(self):
        """合併分類"""
        # 獲取選中的項目
        items = self.tree.selectedItems()
        if len(items) != 2:
            QMessageBox.warning(self, "警告", "請選擇兩個要合併的分類")
            return

        # 取得來源和目標項目
        source_item = items[0]
        target_item = items[1]

        source_parent = source_item.parent()
        target_parent = target_item.parent()

        source_name = source_item.text(0)
        target_name = target_item.text(0)

        # 建立確認訊息
        msg = f"要將「{source_name}」合併到「{target_name}」嗎？"
        if QMessageBox.question(self, "確認合併", msg) != QMessageBox.Yes:
            return

        try:
            # 根據不同情況處理合併
            if not source_parent and not target_parent:
                # 兩個主分類合併
                source_data = self.categories.pop(source_name)
                if 'subcategories' not in self.categories[target_name]:
                    self.categories[target_name]['subcategories'] = {}

                # 合併計數和子分類
                self.categories[target_name]['count'] += source_data['count']
                for sub_name, sub_count in source_data.get('subcategories', {}).items():
                    if sub_name in self.categories[target_name]['subcategories']:
                        self.categories[target_name]['subcategories'][sub_name] += sub_count
                    else:
                        self.categories[target_name]['subcategories'][sub_name] = sub_count

            elif source_parent and target_parent:
                # 兩個子分類合併
                source_parent_name = source_parent.text(0)
                target_parent_name = target_parent.text(0)

                # 取得來源子分類的計數
                source_count = self.categories[source_parent_name]['subcategories'].pop(source_name)

                # 加到目標子分類
                if target_name in self.categories[target_parent_name]['subcategories']:
                    self.categories[target_parent_name]['subcategories'][target_name] += source_count
                else:
                    self.categories[target_parent_name]['subcategories'][target_name] = source_count

            elif source_parent:
                # 子分類合併到主分類
                source_parent_name = source_parent.text(0)
                source_count = self.categories[source_parent_name]['subcategories'].pop(source_name)

                # 加到目標主分類
                self.categories[target_name]['count'] += source_count

            else:
                # 主分類合併到子分類
                source_data = self.categories.pop(source_name)
                target_parent_name = target_parent.text(0)

                # 加到目標子分類
                if target_name in self.categories[target_parent_name]['subcategories']:
                    self.categories[target_parent_name]['subcategories'][target_name] += source_data['count']
                else:
                    self.categories[target_parent_name]['subcategories'][target_name] = source_data['count']

                # 處理來源的子分類
                for sub_name, sub_count in source_data.get('subcategories', {}).items():
                    if sub_name in self.categories[target_parent_name]['subcategories']:
                        self.categories[target_parent_name]['subcategories'][sub_name] += sub_count
                    else:
                        self.categories[target_parent_name]['subcategories'][sub_name] = sub_count

            # 更新顯示
            self.updateTree()
            self.saveConfig()

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"合併分類時發生錯誤：{str(e)}")

    def delete_category(self):
        """刪除分類"""
        item = self.tree.currentItem()
        if item:
            name = item.text(0)
            parent = item.parent()

            reply = QMessageBox.question(
                self, "確認刪除",
                f"確定要刪除分類「{name}」嗎？\n注意：這不會刪除文章中的分類標記。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                if parent:  # 子分類
                    main_cat = parent.text(0)
                    del self.categories[main_cat]['subcategories'][name]
                else:  # 主分類
                    del self.categories[name]
                self.updateTree()
                self.saveConfig()


class TagManager(QDialog):
    """標籤管理視窗"""
    tags_updated = Signal(list)  # 標籤更新信號

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("標籤管理")
        self.setGeometry(200, 200, 500, 400)
        self.tags = {}  # 儲存標籤資料
        self.config_file = Path('tag_config.json')

        self.initUI()
        self.loadConfig()

    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 標籤列表
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['標籤名稱', '使用次數'])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.tree)

        # 按鈕列
        btn_layout = QHBoxLayout()

        select_btn = QPushButton("選擇標籤")  # 新增選擇標籤按鈕
        select_btn.clicked.connect(self.select_tags)
        btn_layout.addWidget(select_btn)

        edit_btn = QPushButton("編輯標籤")
        edit_btn.clicked.connect(self.edit_tag)
        btn_layout.addWidget(edit_btn)

        merge_btn = QPushButton("合併標籤")
        merge_btn.clicked.connect(self.merge_tags)
        btn_layout.addWidget(merge_btn)

        delete_btn = QPushButton("刪除標籤")
        delete_btn.clicked.connect(self.delete_tag)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def loadConfig(self):
        """載入設定檔"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.tags = json.load(f)
                self.updateTree()
            except Exception as e:
                QMessageBox.warning(self, "警告", f"載入設定檔時發生錯誤：{str(e)}")

    def saveConfig(self):
        """儲存設定檔"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.tags, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存設定檔時發生錯誤：{str(e)}")

    def updateTree(self):
        """更新標籤列表"""
        self.tree.clear()
        # 依使用次數排序
        sorted_tags = sorted(self.tags.items(), key=lambda x: x[1], reverse=True)
        for tag, count in sorted_tags:
            QTreeWidgetItem(self.tree, [tag, str(count)])

    def scan_articles(self, articles):
        """掃描文章更新標籤統計"""
        # 重設計數
        self.tags.clear()

        # 統計文章標籤
        for article in articles:
            tags = article.get('tags', [])
            if isinstance(tags, list):
                for tag in tags:
                    self.tags[tag] = self.tags.get(tag, 0) + 1

        self.updateTree()
        self.saveConfig()
        # 發送更新信號
        self.tags_updated.emit(list(self.tags.keys()))

    def select_tags(self):
        """開啟標籤選擇對話框"""
        # 取得目前的標籤
        current_tags = [tag.strip() for tag in self.parent().tags_edit.text().split(',') if tag.strip()]

        # 顯示標籤選擇對話框
        selector = TagSelector(self.tags, current_tags, self)
        if selector.exec() == QDialog.Accepted:
            # 更新標籤輸入框
            selected_tags = selector.get_selected_tags()
            self.parent().tags_edit.setText(', '.join(selected_tags))

    def edit_tag(self):
        """編輯標籤"""
        item = self.tree.currentItem()
        if item:
            old_name = item.text(0)
            new_name, ok = QInputDialog.getText(
                self, "編輯標籤", "請輸入新的標籤名稱：",
                text=old_name
            )
            if ok and new_name and new_name != old_name:
                count = self.tags.pop(old_name)
                self.tags[new_name] = count
                self.updateTree()
                self.saveConfig()

    def merge_tags(self):
        """合併標籤"""
        # 獲取選中的標籤
        items = self.tree.selectedItems()
        if len(items) != 2:
            QMessageBox.warning(self, "警告", "請選擇兩個要合併的標籤")
            return

        tag1 = items[0].text(0)
        tag2 = items[1].text(0)

        # 請使用者選擇要保留的標籤
        msg = f"要將「{tag2}」合併到「{tag1}」嗎？\n" \
              f"（{tag1}的使用次數：{self.tags[tag1]}，" \
              f"{tag2}的使用次數：{self.tags[tag2]}）"
        reply = QMessageBox.question(self, "確認合併", msg)

        if reply == QMessageBox.Yes:
            # 合併計數
            self.tags[tag1] += self.tags[tag2]
            del self.tags[tag2]
            self.updateTree()
            self.saveConfig()

    def delete_tag(self):
        """刪除標籤"""
        item = self.tree.currentItem()
        if item:
            name = item.text(0)
            reply = QMessageBox.question(
                self, "確認刪除",
                f"確定要刪除標籤「{name}」嗎？\n注意：這不會刪除文章中的標籤。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                del self.tags[name]
                self.updateTree()
                self.saveConfig()


class TagSelector(QDialog):
    """標籤選擇對話框"""

    def __init__(self, tags, current_tags=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("選擇標籤")
        self.setGeometry(200, 200, 400, 500)
        self.selected_tags = []

        # 主佈局
        layout = QVBoxLayout()

        # 搜尋框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜尋標籤...")
        self.search_box.textChanged.connect(self.filter_tags)  # 確保這裡的方法名稱一致
        layout.addWidget(self.search_box)

        # 標籤列表
        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QAbstractItemView.MultiSelection)
        # 載入標籤
        for tag, count in sorted(tags.items(), key=lambda x: (-x[1], x[0])):
            item = QListWidgetItem(f"{tag} ({count})")
            item.setData(Qt.UserRole, tag)  # 儲存原始標籤名稱
            self.tag_list.addItem(item)
            # 如果是目前文章已有的標籤,就預先選取
            if current_tags and tag in current_tags:
                item.setSelected(True)
        layout.addWidget(self.tag_list)

        # 按鈕列
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("確定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def filter_tags(self, text):  # 確保方法名稱跟信號連接處一致
        """過濾標籤列表"""
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item:  # 加入檢查確保 item 存在
                tag = item.data(Qt.UserRole)  # 使用儲存的原始標籤名稱
                item.setHidden(text.lower() not in tag.lower())

    def get_selected_tags(self):
        """取得選取的標籤"""
        return [item.data(Qt.UserRole) for item in self.tag_list.selectedItems()]


class CategorySelector(QDialog):
    """分類選擇對話框"""

    def __init__(self, categories, current_categories=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("選擇分類")
        self.setGeometry(200, 200, 400, 500)

        # 主佈局
        layout = QVBoxLayout()

        # 搜尋框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜尋分類...")
        self.search_box.textChanged.connect(self.filter_categories)
        layout.addWidget(self.search_box)

        # 分類樹狀列表
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(['分類名稱', '使用次數'])
        self.category_tree.setSelectionMode(QAbstractItemView.MultiSelection)

        # 載入分類
        for main_cat, data in categories.items():
            # 建立主分類項目
            main_item = QTreeWidgetItem([
                main_cat,
                str(data.get('count', 0))
            ])

            # 如果是目前已選的分類就預先選取
            if current_categories and main_cat in current_categories:
                main_item.setSelected(True)

            # 加入子分類
            for sub_cat, count in data.get('subcategories', {}).items():
                sub_item = QTreeWidgetItem([
                    sub_cat,
                    str(count)
                ])
                # 檢查子分類是否已選取
                full_cat = f"{main_cat}/{sub_cat}"
                if current_categories and full_cat in current_categories:
                    sub_item.setSelected(True)
                main_item.addChild(sub_item)

            self.category_tree.addTopLevelItem(main_item)

        self.category_tree.expandAll()
        layout.addWidget(self.category_tree)

        # 按鈕列
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("確定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def filter_categories(self, text):
        """過濾分類列表"""

        def filter_item(item):
            """遞迴過濾項目"""
            # 取得分類名稱
            category = item.text(0)
            visible = text.lower() in category.lower()

            # 處理子項目
            for i in range(item.childCount()):
                child = item.child(i)
                child_visible = filter_item(child)
                visible = visible or child_visible

            item.setHidden(not visible)
            return visible

        # 過濾所有頂層項目
        for i in range(self.category_tree.topLevelItemCount()):
            item = self.category_tree.topLevelItem(i)
            filter_item(item)

    def get_selected_categories(self):
        """取得選取的分類"""
        categories = []

        def collect_selected(item):
            """遞迴收集選取的項目"""
            if item.isSelected():
                # 如果是子分類,加上父分類路徑
                parent = item.parent()
                if parent:
                    categories.append(f"{parent.text(0)}/{item.text(0)}")
                else:
                    categories.append(item.text(0))

            # 檢查子項目
            for i in range(item.childCount()):
                collect_selected(item.child(i))

        # 收集所有選取的項目
        for i in range(self.category_tree.topLevelItemCount()):
            collect_selected(self.category_tree.topLevelItem(i))

        return categories


class ExportThread(QThread):
    """
    非同步文章匯出器
    使用QThread避免在打包檔案時凍結UI
    """
    finished = Signal()  # 完成信號
    error = Signal(str)  # 錯誤信號
    progress = Signal(int)  # 進度信號

    def __init__(self, source_dir, target_file):
        super().__init__()
        self.source_dir = source_dir
        self.target_file = target_file

    def run(self):
        try:
            import zipfile
            import os

            # 建立 ZIP 檔案
            with zipfile.ZipFile(self.target_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 找出所有需要打包的檔案
                total_files = 0
                files_to_zip = []

                for root, dirs, files in os.walk(self.source_dir):
                    for file in files:
                        # 取得檔案完整路徑
                        full_path = os.path.join(root, file)
                        # 計算相對路徑
                        rel_path = os.path.relpath(full_path, self.source_dir)

                        # 只打包 .md 檔和圖片檔
                        if file.endswith('.md') or \
                                file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                            files_to_zip.append((full_path, rel_path))
                            total_files += 1

                # 開始打包檔案
                for i, (full_path, rel_path) in enumerate(files_to_zip):
                    try:
                        # 加入檔案到 zip
                        zipf.write(full_path, rel_path)
                        # 更新進度
                        progress = int((i + 1) / total_files * 100)
                        self.progress.emit(progress)
                    except Exception as e:
                        print(f"無法加入檔案 {full_path}: {str(e)}")
                        continue

            self.finished.emit()

        except Exception as e:
            self.error.emit(f"匯出文章時發生錯誤: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = HexoEditor()
    window.show()
    sys.exit(app.exec())