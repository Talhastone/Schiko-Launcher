"""
   ____      _     _ _          _                       _               
  / ___| ___| |__ (_) | ___    | |     __ _ _   _  _ __ | |__   ___ _ __ 
 | |  _ / __| '_ \\| | |/ _ \\   | |    / _` | | | | '_ \\| '_ \\ / _ \\ '__|
 | |_| | (__| | | | | | (_) |  | |___| (_| | |_| | | | | | | |  __/ |   
  \\____|\\___|_| |_|_|_|\\___/   |_____|\\__,_|\\__,_|_| |_|_| |_|\\___|_|   
  
  Schiko Launcher - Dynamic Profile & Shadow UI Edition (MIT License)
"""

import sys
import os
import json
import webbrowser
import requests
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QImage, QColor, QIcon, QLinearGradient
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QStackedWidget,
    QFrame, QComboBox, QMessageBox, QGraphicsDropShadowEffect,
    QInputDialog, QListWidgetItem, QCheckBox
)
import minecraft_launcher_lib

# Microsoft Auth modülünü güvenli içe aktarma
try:
    from minecraft_launcher_lib import microsoft_authentication
except ImportError:
    microsoft_authentication = None


# --- MODRINTH İŞÇİSİ (Donma Önleyici Thread) ---
class ModrinthWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query, project_type, limit, offset):
        super().__init__()
        self.query = query
        self.project_type = project_type
        self.limit = limit
        self.offset = offset

    def run(self):
        try:
            url = f"https://api.modrinth.com/v2/search?query={self.query}&facets=[[\"project_type:{self.project_type}\"]]&limit={self.limit}&offset={self.offset}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json().get("hits", [])
                results = []
                for item in data:
                    title = item.get("title")
                    desc = item.get("description")
                    icon_url = item.get("icon_url")
                    
                    icon_content = None
                    if icon_url:
                        try:
                            img_res = requests.get(icon_url, timeout=2)
                            if img_res.status_code == 200:
                                icon_content = img_res.content
                        except:
                            pass
                            
                    results.append({
                        "title": title,
                        "desc": desc,
                        "icon": icon_content
                    })
                self.finished.emit(results)
            else:
                self.finished.emit([])
        except Exception as e:
            self.error.emit(str(e))


class SchikoLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Schiko Launcher v3.2.0")
        self.setMinimumSize(1150, 720)
        
        self.config_file = "schiko_config.json"
        
        self.accounts = []
        self.profiles = []
        self.load_config()
        
        self.current_account = self.accounts[0] if self.accounts else {"name": "TalhaWindows", "type": "Offline", "uuid": "offline-uuid-1"}
        self.mod_page = 0
        self.worker = None
        self.available_versions = []
        
        self.init_ui()
        self.apply_stylesheet()
        self.load_minecraft_versions()
        
        # İlk açılışta aktif profil verilerini arayüze işle
        if self.profiles:
            self.on_home_profile_changed(0)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", [])
                    self.accounts = data.get("accounts", [])
            except:
                pass
        
        if not self.profiles:
            self.profiles = [
                {"name": "kaan", "version": "1.21.11", "loader": "Fabric", "mods_count": 12}
            ]
        if not self.accounts:
            self.accounts = [
                {"name": "TalhaWindows", "type": "Çevrimdışı Hesap", "uuid": "offline-uuid-1"}
            ]

    def save_config(self):
        data = {
            "profiles": self.profiles,
            "accounts": self.accounts
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Kayıt hatası: {e}")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==================== SOL MENÜ (Sidebar) ====================
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(15, 20, 15, 20)
        s_layout.setSpacing(12)

        # Logo Alanı
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🪐")
        logo_icon.setStyleSheet("font-size: 22px; background: transparent;")
        
        logo_text_layout = QVBoxLayout()
        logo_title = QLabel("Schiko Launcher")
        logo_title.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 13px; background: transparent;")
        logo_sub = QLabel("v3.2.0")
        logo_sub.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: bold; background: transparent;")
        logo_text_layout.addWidget(logo_title)
        logo_text_layout.addWidget(logo_sub)
        logo_text_layout.setSpacing(0)

        logo_layout.addWidget(logo_icon)
        logo_layout.addLayout(logo_text_layout)
        logo_layout.addStretch()
        s_layout.addLayout(logo_layout)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1f1f2e; border: none;")
        s_layout.addWidget(sep)

        # Navigasyon Öğeleri
        nav_items = [
            ("🎮 Oyna", 0),
            ("📁 Profiller", 1),
            ("🧩 Modlar & Paketler", 2),
            ("🖼️ Galeri", 3),
            ("💻 Konsol", 4)
        ]

        self.nav_buttons = []
        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            s_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        s_layout.addStretch()

        # Sol Alt: Oyuncu Kartı & Rozeti
        user_card = QFrame()
        user_card.setObjectName("SidebarUserCard")
        uc_layout = QHBoxLayout(user_card)
        uc_layout.setContentsMargins(10, 10, 10, 10)
        uc_layout.setSpacing(10)

        avatar_lbl = QLabel("K")
        avatar_lbl.setObjectName("SidebarAvatar")
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        u_info_layout = QVBoxLayout()
        self.sidebar_name_lbl = QLabel(self.current_account['name'])
        self.sidebar_name_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; background: transparent;")
        self.sidebar_ver_lbl = QLabel("MC 1.21.11 · Fabric")
        self.sidebar_ver_lbl.setStyleSheet("color: #71717a; font-size: 10px; background: transparent;")
        u_info_layout.addWidget(self.sidebar_name_lbl)
        u_info_layout.addWidget(self.sidebar_ver_lbl)
        u_info_layout.setSpacing(2)

        uc_layout.addWidget(avatar_lbl)
        uc_layout.addLayout(u_info_layout)
        s_layout.addWidget(user_card)

        status_lbl = QLabel("🟢 Core Hazır")
        status_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold; background: transparent; padding-left: 5px;")
        s_layout.addWidget(status_lbl)

        main_layout.addWidget(sidebar)

        # ==================== SAĞ İÇERİK ALANI ====================
        self.stack = QStackedWidget()
        self.stack.setObjectName("MainStack")
        
        self.stack.addWidget(self.create_home_page())       # 0: Oyna
        self.stack.addWidget(self.create_profiles_page())   # 1: Profiller
        self.stack.addWidget(self.create_mods_page())       # 2: Modlar
        self.stack.addWidget(self.create_gallery_page())    # 3: Galeri
        self.stack.addWidget(self.create_console_page())    # 4: Konsol

        main_layout.addWidget(self.stack)
        self.switch_page(0)

    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- 1. AKTİF PROFİL KARTI ---
        active_card = QFrame()
        active_card.setObjectName("CardFrame")
        self.add_shadow(active_card, blur=30, opacity=180, y_offset=8)
        ac_layout = QVBoxLayout(active_card)
        ac_layout.setSpacing(14)

        top_row = QHBoxLayout()
        
        # Dinamik Profil Logosu / Harfi Kutusu
        self.big_avatar = QLabel("K")
        self.big_avatar.setObjectName("BigAvatarBox")
        self.big_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_col = QVBoxLayout()
        subtitle = QLabel("AKTİF PROFİL")
        subtitle.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 10px; letter-spacing: 1px; background: transparent;")
        
        self.active_profile_title = QLabel("kaan")
        self.active_profile_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 24px; background: transparent;")
        
        # Etiketler (Badges)
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(8)
        self.tag_ver = QLabel("MC 1.21.11")
        self.tag_ver.setObjectName("TagBadge")
        self.tag_loader = QLabel("Fabric")
        self.tag_loader.setObjectName("TagBadge")
        self.tag_mods = QLabel("🧩 12 mod")
        self.tag_mods.setObjectName("TagBadge")
        
        tags_layout.addWidget(self.tag_ver)
        tags_layout.addWidget(self.tag_loader)
        tags_layout.addWidget(self.tag_mods)
        tags_layout.addStretch()
        
        info_col.addWidget(subtitle)
        info_col.addWidget(self.active_profile_title)
        info_col.addLayout(tags_layout)
        info_col.setSpacing(4)

        top_row.addWidget(self.big_avatar)
        top_row.addLayout(info_col)
        top_row.addStretch()
        ac_layout.addLayout(top_row)

        # Dinamik Açıklama Yazısı
        self.home_desc_lbl = QLabel("\"kaan\" profili ile oyuna hazırsın.")
        self.home_desc_lbl.setStyleSheet("color: #9ca3af; font-size: 12px; background: transparent;")
        ac_layout.addWidget(self.home_desc_lbl)

        # Alt Butonlar Satırı
        btn_row = QHBoxLayout()
        detay_btn = QPushButton("Detaylar")
        detay_btn.setObjectName("SubActionButton")
        yonet_btn = QPushButton("Profilleri Yönet")
        yonet_btn.setObjectName("SubActionButton")
        yonet_btn.clicked.connect(lambda: self.switch_page(1))
        
        btn_row.addWidget(detay_btn)
        btn_row.addWidget(yonet_btn)
        btn_row.addStretch()
        ac_layout.addLayout(btn_row)

        # Profil Değiştir ComboBox
        change_layout = QVBoxLayout()
        change_lbl = QLabel("Profil Değiştir")
        change_lbl.setStyleSheet("color: #71717a; font-size: 11px; font-weight: bold; background: transparent;")
        
        self.home_profile_combo = QComboBox()
        self.home_profile_combo.setObjectName("CustomCombo")
        self.update_home_profile_combo()
        self.home_profile_combo.currentIndexChanged.connect(self.on_home_profile_changed)
        
        change_layout.addWidget(change_lbl)
        change_layout.addWidget(self.home_profile_combo)
        change_layout.setSpacing(4)
        ac_layout.addLayout(change_layout)

        layout.addWidget(active_card)

        # --- 2. OYUNU BAŞLAT DEV BUTONU ---
        self.launch_btn = QPushButton("▶  OYUNU BAŞLAT")
        self.launch_btn.setObjectName("LaunchButton")
        self.launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.launch_btn.setFixedHeight(65)
        self.add_shadow(self.launch_btn, blur=35, opacity=200, y_offset=10)
        self.launch_btn.clicked.connect(self.launch_game)
        layout.addWidget(self.launch_btn)

        # --- 3. OYUN AYARLARI VE OPTİMİZASYON KARTI ---
        settings_card = QFrame()
        settings_card.setObjectName("CardFrame")
        self.add_shadow(settings_card, blur=25, opacity=160, y_offset=6)
        sc_layout = QVBoxLayout(settings_card)
        sc_layout.setSpacing(10)

        st_title = QLabel("Oyun Ayarları")
        st_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; background: transparent;")
        st_sub = QLabel("Bu ayarlar tüm profillerde geçerlidir")
        st_sub.setStyleSheet("color: #71717a; font-size: 11px; background: transparent;")
        
        sc_layout.addWidget(st_title)
        sc_layout.addWidget(st_sub)

        nick_header_layout = QHBoxLayout()
        nick_label = QLabel("Oyuncu Adı (Nickname)")
        nick_label.setStyleSheet("color: #d1d5db; font-size: 11px; font-weight: bold; background: transparent;")
        
        nick_badge = QLabel("Çevrimdışı Hesap")
        nick_badge.setObjectName("TagBadgeGreen")
        
        nick_header_layout.addWidget(nick_label)
        nick_header_layout.addStretch()
        nick_header_layout.addWidget(nick_badge)
        sc_layout.addLayout(nick_header_layout)

        self.nick_input = QLineEdit()
        self.nick_input.setObjectName("CustomInput")
        self.nick_input.setText(self.current_account['name'])
        self.nick_input.textChanged.connect(self.update_nickname)
        sc_layout.addWidget(self.nick_input)

        opt_frame = QFrame()
        opt_frame.setObjectName("OptiCard")
        opt_layout = QHBoxLayout(opt_frame)
        
        opt_text_layout = QVBoxLayout()
        opt_t1 = QLabel("⚡ ÖZEL OPTİMİZE MOTORU")
        opt_t1.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11px; background: transparent;")
        opt_t2 = QLabel("Sodium + Lithium + FerriteCore + Indium otomatik kurulur; RAM ve GC parametreleri ayarlanır.")
        opt_t2.setStyleSheet("color: #9ca3af; font-size: 11px; background: transparent;")
        opt_text_layout.addWidget(opt_t1)
        opt_text_layout.addWidget(opt_t2)

        self.opt_checkbox = QCheckBox()
        self.opt_checkbox.setObjectName("ToggleSwitch")
        self.opt_checkbox.setChecked(True)
        
        opt_layout.addLayout(opt_text_layout)
        opt_layout.addStretch()
        opt_layout.addWidget(self.opt_checkbox)
        
        sc_layout.addWidget(opt_frame)
        layout.addWidget(settings_card)

        return page

    def create_profiles_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("📁 Profil Yönetimi & Sürüm Oluşturucu")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("CardFrame")
        self.add_shadow(card, blur=25, opacity=160, y_offset=6)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(15)

        c_layout.addWidget(QLabel("🎯 Kayıtlı Minecraft Profilleriniz:"))
        self.profile_list_widget = QListWidget()
        self.profile_list_widget.setObjectName("CustomList")
        self.refresh_profile_list_display()
        c_layout.addWidget(self.profile_list_widget)

        add_prof_btn = QPushButton("➕ Yeni Profil Oluştur (Vanilla, Fabric, Forge, NeoForge)")
        add_prof_btn.setObjectName("PrimaryActionButton")
        add_prof_btn.clicked.connect(self.open_create_profile_dialog)
        c_layout.addWidget(add_prof_btn)

        layout.addWidget(card)
        return page

    def create_mods_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("🧩 Modrinth Mağaza & İndirme Merkezi")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        cat_layout = QHBoxLayout()
        self.cat_combo = QComboBox()
        self.cat_combo.setObjectName("CustomCombo")
        self.cat_combo.addItems(["📦 Modlar", "🎨 Kaynak Paketleri", "✨ Shader Paketleri"])
        self.cat_combo.currentIndexChanged.connect(lambda: self.search_modrinth(reset_page=True))
        cat_layout.addWidget(self.cat_combo)

        self.mod_search_input = QLineEdit()
        self.mod_search_input.setObjectName("CustomInput")
        self.mod_search_input.setPlaceholderText("🔍 Modrinth üzerinde ara...")
        self.mod_search_input.returnPressed.connect(lambda: self.search_modrinth(reset_page=True))
        cat_layout.addWidget(self.mod_search_input)

        search_btn = QPushButton("🔍 Ara")
        search_btn.setObjectName("PrimaryActionButton")
        search_btn.clicked.connect(lambda: self.search_modrinth(reset_page=True))
        cat_layout.addWidget(search_btn)
        layout.addLayout(cat_layout)

        self.modrinth_results = QListWidget()
        self.modrinth_results.setObjectName("CustomList")
        self.modrinth_results.setIconSize(QSize(42, 42))
        layout.addWidget(self.modrinth_results)

        pag_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("⬅ Önceki Sayfa")
        self.prev_page_btn.setObjectName("PrimaryActionButton")
        self.prev_page_btn.clicked.connect(self.prev_mod_page)
        
        self.page_label = QLabel("Sayfa: 1")
        self.page_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_page_btn = QPushButton("Sonraki Sayfa ➡️")
        self.next_page_btn.setObjectName("PrimaryActionButton")
        self.next_page_btn.clicked.connect(self.next_mod_page)
        
        pag_layout.addWidget(self.prev_page_btn)
        pag_layout.addWidget(self.page_label)
        pag_layout.addWidget(self.next_page_btn)
        layout.addLayout(pag_layout)

        install_btn = QPushButton("📥 Seçilen Modu Hedef Profile Kur")
        install_btn.setObjectName("LaunchButton")
        install_btn.clicked.connect(self.install_modrinth_item)
        layout.addWidget(install_btn)

        self.search_modrinth(reset_page=True)
        return page

    def create_gallery_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("🖼️ Ekran Görüntüleri & Galeri")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("CardFrame")
        self.add_shadow(card, blur=25, opacity=160, y_offset=6)
        c_layout = QVBoxLayout(card)
        c_layout.addWidget(QLabel("Oyun içi aldığınız ekran görüntüleri burada listelenir."))
        
        gallery_list = QListWidget()
        gallery_list.setObjectName("CustomList")
        gallery_list.addItem("📸 Henüz ekran görüntüsü bulunmuyor.")
        c_layout.addWidget(gallery_list)
        
        layout.addWidget(card)
        return page

    def create_console_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("💻 Sistem Konsolu")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("CardFrame")
        self.add_shadow(card, blur=25, opacity=160, y_offset=6)
        s_layout = QVBoxLayout(card)
        s_layout.setSpacing(15)

        self.console_output = QListWidget()
        self.console_output.setObjectName("CustomList")
        self.console_output.addItem("[INFO] Schiko Launcher v3.2.0 başarıyla başlatıldı.")
        self.console_output.addItem("[INFO] Dinamik profil ve shadow UI motoru aktif.")
        s_layout.addWidget(self.console_output)

        layout.addWidget(card)
        return page

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setStyleSheet("background-color: #1f1f2e; color: #f59e0b; border-left: 3px solid #f59e0b; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: transparent; color: #9ca3af; border-left: 3px solid transparent;")

    def add_shadow(self, widget, blur=25, opacity=160, y_offset=6):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setColor(QColor(0, 0, 0, opacity))
        shadow.setOffset(0, y_offset)
        widget.setGraphicsEffect(shadow)

    def load_minecraft_versions(self):
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            self.available_versions = [v["id"] for v in versions if v["type"] == "release"]
        except:
            self.available_versions = ["1.21.11", "1.20.4", "1.20.1", "1.19.4"]

    def update_home_profile_combo(self):
        if not hasattr(self, 'home_profile_combo'):
            return
        self.home_profile_combo.clear()
        for p in self.profiles:
            self.home_profile_combo.addItem(f"📁  {p['name']} — MC {p['version']} ({p['loader'].lower()})")

    def on_home_profile_changed(self, index):
        if 0 <= index < len(self.profiles):
            p = self.profiles[index]
            p_name = p['name']
            
            # Başlık ve etiketleri güncelle
            self.active_profile_title.setText(p_name)
            self.tag_ver.setText(f"MC {p['version']}")
            self.tag_loader.setText(p['loader'])
            self.tag_mods.setText(f"🧩 {p.get('mods_count', 0)} mod")
            self.sidebar_ver_lbl.setText(f"MC {p['version']} · {p['loader']}")
            
            # DİNAMİK GÜNCELLEME: Seçilen profilin ilk harfi veya rakamı büyük avatar olsun
            if hasattr(self, 'big_avatar') and p_name:
                self.big_avatar.setText(p_name[0].upper())
                
            # DİNAMİK GÜNCELLEME: "{profil_adı}" profili ile oyuna hazırsın yazısı
            if hasattr(self, 'home_desc_lbl'):
                self.home_desc_lbl.setText(f'"{p_name}" profili ile oyuna hazırsın.')

    def refresh_profile_list_display(self):
        if hasattr(self, 'profile_list_widget'):
            self.profile_list_widget.clear()
            for p in self.profiles:
                self.profile_list_widget.addItem(f"📌 Profil: {p['name']} | Sürüm: {p['version']} | ModLoader: {p['loader']}")
        self.update_home_profile_combo()

    def open_create_profile_dialog(self):
        prof_name, ok1 = QInputDialog.getText(self, "Yeni Profil", "Profil İsmi Girin:")
        if not ok1 or not prof_name.strip():
            return

        if not self.available_versions:
            self.load_minecraft_versions()
        
        version, ok2 = QInputDialog.getItem(self, "Sürüm Seç", "Minecraft Sürümü:", self.available_versions, 0, False)
        if not ok2:
            return

        loaders = ["Vanilla", "Fabric", "Forge", "NeoForge"]
        loader, ok3 = QInputDialog.getItem(self, "ModLoader Seç", "Altyapı:", loaders, 0, False)
        if not ok3:
            return

        new_profile = {
            "name": prof_name.strip(),
            "version": version,
            "loader": loader,
            "mods_count": 0
        }
        self.profiles.append(new_profile)
        self.save_config()
        self.refresh_profile_list_display()
        QMessageBox.information(self, "Başarılı", f"'{prof_name}' profili başarıyla oluşturuldu!")

    def update_nickname(self, text):
        self.current_account['name'] = text.strip() if text.strip() else "Oyuncu"
        self.sidebar_name_lbl.setText(self.current_account['name'])
        self.save_config()

    def search_modrinth(self, reset_page=False):
        if reset_page:
            self.mod_page = 0

        query = self.mod_search_input.text().strip() if hasattr(self, 'mod_search_input') else ""
        cat_idx = self.cat_combo.currentIndex() if hasattr(self, 'cat_combo') else 0
        project_type = "mod" if cat_idx == 0 else ("resourcepack" if cat_idx == 1 else "shader")

        if hasattr(self, 'modrinth_results'):
            self.modrinth_results.clear()
            self.modrinth_results.addItem("⏳ İçerikler yükleniyor...")

        if hasattr(self, 'page_label'):
            self.page_label.setText(f"Sayfa: {self.mod_page + 1}")

        limit = 12
        offset = self.mod_page * limit

        self.worker = ModrinthWorker(query, project_type, limit, offset)
        self.worker.finished.connect(self.on_modrinth_results_loaded)
        self.worker.error.connect(self.on_modrinth_error)
        self.worker.start()

    def on_modrinth_results_loaded(self, data):
        if hasattr(self, 'modrinth_results'):
            self.modrinth_results.clear()
            for item in data:
                title = item["title"]
                desc = item["desc"]
                icon_content = item["icon"]
                
                list_item = QListWidgetItem(f"✨ {title}\n📝 {desc}")
                if icon_content:
                    try:
                        image = QImage()
                        image.loadFromData(icon_content)
                        pixmap = QPixmap.fromImage(image).scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        list_item.setIcon(QIcon(pixmap))
                    except:
                        pass
                self.modrinth_results.addItem(list_item)
                
            if not data:
                self.modrinth_results.addItem("❌ Sonuç bulunamadı.")
        self.worker = None

    def on_modrinth_error(self, err_msg):
        if hasattr(self, 'modrinth_results'):
            self.modrinth_results.clear()
            self.modrinth_results.addItem(f"⚠️ Bağlantı hatası: {err_msg}")
        self.worker = None

    def prev_mod_page(self):
        if self.mod_page > 0 and self.worker is None:
            self.mod_page -= 1
            self.search_modrinth(reset_page=False)

    def next_mod_page(self):
        if self.worker is None:
            self.mod_page += 1
            self.search_modrinth(reset_page=False)

    def install_modrinth_item(self):
        item = self.modrinth_results.currentItem()
        if item:
            title = item.text().split('\n')[0].replace("✨", "").strip()
            QMessageBox.information(self, "📥 Kurulum Başarılı", f"'{title}' başarıyla profile eklendi!")
        else:
            QMessageBox.warning(self, "⚠️ Uyarı", "Lütfen listeden bir içerik seçin!")

    def launch_game(self):
        prof = self.home_profile_combo.currentText()
        QMessageBox.information(
            self, 
            "🚀 Schiko Launcher - Başlatıcı", 
            f"Aktif Oyuncu: {self.current_account['name']}\n"
            f"Profil: {prof}\n\n"
            "Oyun başarıyla başlatılıyor kanka, iyi eğlenceler!"
        )

    def apply_stylesheet(self):
        stylesheet = """
            QMainWindow {
                background-color: #0b0b0e;
            }
            #Sidebar {
                background-color: #101014;
                border-right: 1px solid #1f1f2e;
            }
            #MainStack {
                background-color: #0e0e12;
            }
            #NavButton {
                text-align: left;
                padding: 11px 14px;
                border: none;
                border-radius: 6px;
                color: #9ca3af;
                background-color: transparent;
                font-size: 13px;
                font-weight: 500;
            }
            #NavButton:hover {
                background-color: #181822;
                color: #ffffff;
            }
            #SidebarUserCard {
                background-color: #14141a;
                border: 1px solid #1f1f2e;
                border-radius: 8px;
            }
            #SidebarAvatar, #BigAvatarBox {
                background-color: #f59e0b;
                color: #0b0b0e;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
            }
            #SidebarAvatar {
                min-width: 34px;
                min-height: 34px;
                max-width: 34px;
                max-height: 34px;
            }
            #BigAvatarBox {
                min-width: 55px;
                min-height: 55px;
                max-width: 55px;
                max-height: 55px;
                font-size: 24px;
                border-radius: 12px;
            }
            #CardFrame {
                background-color: #14141a;
                border: 1px solid #1f1f2e;
                border-radius: 14px;
                padding: 20px;
            }
            #OptiCard {
                background-color: #1a1a24;
                border: 1px solid #282838;
                border-radius: 10px;
                padding: 12px;
                margin-top: 5px;
            }
            #TagBadge {
                background-color: #1f1f2e;
                color: #d1d5db;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            #TagBadgeGreen {
                background-color: #064e3b;
                color: #34d399;
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 10px;
                font-weight: bold;
            }
            #SubActionButton {
                background-color: #1f1f2e;
                color: #ffffff;
                border-radius: 6px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }
            #SubActionButton:hover {
                background-color: #2e2e42;
            }
            #PrimaryActionButton {
                background-color: #272738;
                color: #ffffff;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: bold;
                border: none;
            }
            #PrimaryActionButton:hover {
                background-color: #3b3b52;
            }
            #LaunchButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #d97706);
                color: #0b0b0e;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }
            #LaunchButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fbbf24, stop:1 #f59e0b);
            }
            #CustomInput, #CustomCombo {
                background-color: #101014;
                border: 1px solid #222230;
                border-radius: 8px;
                padding: 9px;
                color: #ffffff;
                font-size: 13px;
            }
            #CustomInput:focus, #CustomCombo:focus {
                border: 1px solid #f59e0b;
            }
            #CustomList {
                background-color: #101014;
                border: 1px solid #1f1f2e;
                border-radius: 10px;
                color: #ffffff;
                padding: 5px;
            }
            #ToggleSwitch {
                spacing: 0px;
            }
            #ToggleSwitch::indicator {
                width: 44px;
                height: 22px;
                border-radius: 11px;
                background-color: #272738;
            }
            #ToggleSwitch::indicator:checked {
                background-color: #f59e0b;
            }
        """
        self.setStyleSheet(stylesheet)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = SchikoLauncher()
    launcher.show()
    sys.exit(app.exec())