"""Localization layer.

Every user-visible string lives here. The UI can switch language at runtime
without restarting: call ``set_lang("tr")`` and re-render.
"""

from __future__ import annotations

DEFAULT_LANG = "en"
LANGUAGES = {"en": "English", "tr": "Türkçe"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ---------------- window / static labels
        "ui.title": "AFK Game Downloader Pro",
        "ui.subtitle": "v{version}  ·  Steam + Epic",
        "ui.when_finish": "When downloads finish:",
        "ui.countdown": "Countdown:",
        "ui.verify": "Verify for:",
        "ui.sec": "s",
        "ui.steam": "Steam",
        "ui.epic": "Epic",
        "ui.btn_start": "Start monitoring",
        "ui.btn_stop": "Stop",
        "ui.btn_cancel": "Cancel",
        "ui.btn_kill": "Shut down now",
        "ui.event_log": "Event log",
        "ui.lang_button": "TR",
        "ui.lang_tooltip": "Switch to Turkish",
        "ui.empty": "No active downloads.\nStart a download in Steam or Epic.",
        "ui.last_check": "Last check {time}",
        "ui.net": "net {mbps:.1f} Mbps",
        "ui.auto_refresh": "auto-refresh {seconds}s",
        "ui.disk": "disk {speed}",
        "ui.watch": "Watch",
        "ui.refresh": "Refresh",
        "ui.found": "{count} download(s) found  ·  {watching} watched",
        "ui.found_none": "No active downloads found",
        "ui.row_completed": "completed",
        "ui.row_installed": "fully installed",
        "ui.row_downloading": "downloading...",
        "ui.confirm_kill_title": "Confirm",
        "ui.confirm_kill_body": "Do you want to {action} right now?\n(Running downloads are ignored)",
        "ui.confirm_close_title": "Countdown running",
        "ui.confirm_close_body": "{seconds}s until shutdown.\nClosing the app cancels that action. Are you sure?",
        "ui.error_title": "Error",
        "ui.kill_failed": "Action failed: {error}",
        # ---------------- phases
        "phase.stopped": "STOPPED",
        "phase.waiting": "WAITING FOR DOWNLOAD",
        "phase.downloading": "DOWNLOADING",
        "phase.draining": "VERIFYING COMPLETION",
        "phase.ready": "COMPLETED",
        "phase.done": "ACTION TAKEN",
        "phase.interrupted": "DOWNLOAD INTERRUPTED",
        # ---------------- banner details
        "detail.waiting": "Start a download in Steam or Epic — I'll handle the rest.",
        "detail.active": "{count} active download(s)",
        "detail.active_others": "{count} watched  ·  {others} ignored",
        "detail.nowatch": "Nothing is selected. Tick a game to watch it.",
        "detail.draining": "{seconds}s left in the verification window",
        "detail.ready": "{seconds}s until: {action}",
        "detail.stopped": "Monitoring is off. Press \"Start monitoring\".",
        # ---------------- actions
        "action.shutdown": "Shut down computer",
        "action.restart": "Restart",
        "action.sleep": "Sleep",
        "action.hibernate": "Hibernate",
        "action.test": "Test mode (no shutdown)",
        # ---------------- row notes
        "row.on_disk": "on disk {size}",
        "row.queued": "queued (another download is running)",
        "row.no_progress": "progress unknown",
        # ---------------- units / relative time
        "unit.per_second": "/s",
        "dur.seconds": "{s}s",
        "dur.minutes": "{m}m {s:02d}s",
        "dur.hours": "{h}h {m:02d}m",
        "time.now": "now",
        "time.sec_ago": "{n}s ago",
        "time.min_ago": "{n}m ago",
        "time.hour_ago": "{n}h ago",
        # ---------------- event log
        "log.app_started": "AFK Game Downloader Pro started.",
        "log.steam_root": "Steam root: {path}",
        "log.steam_libs": "Steam libraries: {paths}",
        "log.epic_found": "Epic: manifest folder found",
        "log.epic_missing": "Epic: manifest folder not found (Epic may not be installed)",
        "log.watching": "Monitoring started. Waiting for a download...",
        "log.stopped": "Monitoring stopped.",
        "log.cancel_ok": "Shutdown cancelled. Monitoring stopped.",
        "log.cancel_none": "Nothing to cancel; monitoring stopped.",
        "log.download_detected": "Download detected: {names}",
        "log.tracking": "Now tracking: {name}",
        "log.drain_started": "Download stopped. {seconds}s verification window started...",
        "log.evidence": "Proof: {details}",
        "log.recheck_failed": "Final check failed - action cancelled, verifying again.",
        "log.nothing_watched": "No download is ticked any more - back to waiting.",
        "log.interrupted_missing": "Steam download data disappeared - the download was interrupted, monitoring stopped.",
        "log.completed": "COMPLETED: {names}",
        "log.action_in": "Action in {seconds}s: {action}",
        "log.resumed": "A new download started — shutdown cancelled.",
        "log.test_mode": "TEST MODE: '{action}' was not executed (simulated).",
        "log.executing": "Executing action: {action}",
        "log.action_failed": "Action failed: {error}",
        "log.steam_scan_error": "Steam scan failed: {error}",
        "log.epic_scan_error": "Epic scan failed: {error}",
        "log.unexpected": "Unexpected error: {error}",
        "log.refresh": "Refreshed: {active} download(s) found, {added} added.",
        "log.new_download": "Added to the list: {name}",
        "log.unwatched": "Ignored: {name}",
        # ---------------- verification reasons
        "verify.no_tracked": "no downloads were tracked",
        "verify.steam_rate": "Steam is still downloading ({mbps:.1f} Mbps)",
        "verify.manifest_missing": "{name}: appmanifest not found",
        "verify.not_installed": "{name}: not fully installed yet (flags={flags})",
        "verify.log_state": "{name}: Steam log state is '{state}'",
        "verify.bytes_missing": "{name}: bytes missing ({got} / {total})",
        "verify.epic_manifest_missing": "{name}: Epic manifest not found",
        "verify.epic_downloading": "{name}: Epic is still downloading",
        "verify.unknown_source": "unknown source: {key}",
        "verify.still_active": "{name} is still active",
        "verify.ok": "ok",
        # ---------------- setup wizard
        "setup.title": "AFK Game Downloader Pro Setup",
        "setup.step": "Step {current} of {total}",
        "setup.welcome_title": "Welcome to AFK Game Downloader Pro",
        "setup.welcome_body": (
            "This wizard will install AFK Game Downloader Pro on your computer.\n\n"
            "It watches your Steam and Epic Games downloads and powers the PC off "
            "when they are really finished.\n\n"
            "Click Next to continue."
        ),
        "setup.lang_title": "Select language",
        "setup.lang_body": "Choose the language for the installer and for the application.",
        "setup.lang_hint": "You can change it later from the app with the TR/EN button.",
        "setup.license_title": "License Agreement",
        "setup.license_body": "AFK Game Downloader Pro is free software released under the MIT License.",
        "setup.license_accept": "I accept the terms of the MIT License",
        "setup.license_required": "Accept the license to continue.",
        "setup.dest_title": "Choose install location",
        "setup.dest_body": (
            "Setup will install AFK Game Downloader Pro into the folder below.\n"
            "It installs for the current user only, so administrator rights are not needed."
        ),
        "setup.browse": "Browse...",
        "setup.exists": "An existing installation was found here; it will be upgraded.",
        "setup.tasks_title": "Additional tasks",
        "setup.tasks_body": "Choose the shortcuts and options you want.",
        "setup.task_desktop": "Create a desktop shortcut",
        "setup.task_startmenu": "Create a Start Menu shortcut",
        "setup.ready_title": "Ready to install",
        "setup.ready_body": "Setup is ready to begin installing AFK Game Downloader Pro.",
        "setup.summary_dest": "Install location",
        "setup.summary_tasks": "Tasks",
        "setup.none": "(none)",
        "setup.installing_title": "Installing",
        "setup.installing_body": "Please wait while Setup installs AFK Game Downloader Pro.",
        "setup.msg_prepare": "Preparing the destination...",
        "setup.msg_copy": "Copying application files...",
        "setup.msg_shortcuts": "Creating shortcuts...",
        "setup.msg_register": "Registering the application...",
        "setup.msg_uninstaller": "Writing the uninstaller...",
        "setup.msg_done": "Installation complete.",
        "setup.finish_title": "Installation complete",
        "setup.finish_body": "Setup has finished installing AFK Game Downloader Pro on your computer.",
        "setup.launch": "Launch AFK Game Downloader Pro",
        "setup.btn_back": "Back",
        "setup.btn_next": "Next",
        "setup.btn_install": "Install",
        "setup.btn_finish": "Finish",
        "setup.btn_cancel": "Cancel",
        "setup.err_title": "Installation failed",
        "setup.err_space": "Not enough free space in the selected folder.",
        "setup.err_system": "That folder is reserved by Windows. Choose another one.",
        "setup.err_exe_missing": "The bundled application file is missing. Rebuild the installer.",
        "setup.cancel_title": "Cancel setup",
        "setup.cancel_body": "Do you want to quit the installation?",
        "setup.launch_failed": "Could not start the application: {error}",
        # ---------------- uninstall wizard
        "uninstall.title": "Uninstall AFK Game Downloader Pro",
        "uninstall.heading": "Remove AFK Game Downloader Pro from this computer?",
        "uninstall.body": "The following will be removed:",
        "uninstall.item_app": "The application and its files",
        "uninstall.item_shortcuts": "Desktop and Start Menu shortcuts",
        "uninstall.item_settings": "Your settings and event log",
        "uninstall.btn": "Uninstall",
        "uninstall.cancel": "Cancel",
        "uninstall.progress": "Removing...",
        "uninstall.msg_stop": "Closing the application...",
        "uninstall.msg_shortcuts": "Removing shortcuts...",
        "uninstall.msg_registry": "Cleaning the registry...",
        "uninstall.msg_settings": "Removing settings...",
        "uninstall.msg_files": "Removing program files...",
        "uninstall.msg_done": "Done.",
        "uninstall.done_title": "AFK Game Downloader Pro has been removed",
        "uninstall.done_body": "The application, its shortcuts and its registry entries have been deleted.\nAny remaining folder is removed a few seconds after this window closes.",
        "uninstall.close": "Close",

        # ---------------- misc / shell
        "shell.already_running": "AFK Game Downloader Pro is already running.\nCheck its window in the taskbar.",
        "shell.crash": "AFK Game Downloader Pro crashed:\n\n{error}\n\nDetails: {path}",
    },
    "tr": {
        # ---------------- window / static labels
        "ui.title": "AFK Game Downloader Pro",
        "ui.subtitle": "v{version}  ·  Steam + Epic",
        "ui.when_finish": "İndirme bitince:",
        "ui.countdown": "Geri sayım:",
        "ui.verify": "Doğrulama:",
        "ui.sec": "sn",
        "ui.steam": "Steam",
        "ui.epic": "Epic",
        "ui.btn_start": "İzlemeyi başlat",
        "ui.btn_stop": "Durdur",
        "ui.btn_cancel": "İptal",
        "ui.btn_kill": "Şimdi kapat",
        "ui.event_log": "Olay günlüğü",
        "ui.lang_button": "EN",
        "ui.lang_tooltip": "İngilizce'ye geç",
        "ui.empty": "Aktif indirme yok.\nSteam veya Epic'te bir indirme başlat.",
        "ui.last_check": "Son kontrol {time}",
        "ui.net": "ağ {mbps:.1f} Mbps",
        "ui.auto_refresh": "otomatik yenileme {seconds} sn",
        "ui.disk": "disk {speed}",
        "ui.watch": "İzle",
        "ui.refresh": "Yenile",
        "ui.found": "{count} indirme bulundu  ·  {watching} izleniyor",
        "ui.found_none": "Aktif indirme bulunamadı",
        "ui.row_completed": "tamamlandı",
        "ui.row_installed": "tam kurulu",
        "ui.row_downloading": "indiriliyor...",
        "ui.confirm_kill_title": "Onay",
        "ui.confirm_kill_body": "Şimdi şu işlem yapılsın mı?\n\n{action}\n\n(Süren indirmeler yok sayılır)",
        "ui.confirm_close_title": "Geri sayım sürüyor",
        "ui.confirm_close_body": "{seconds} sn sonra kapatma yapılacak.\nProgramı kapatırsan bu işlem iptal olur. Emin misin?",
        "ui.error_title": "Hata",
        "ui.kill_failed": "İşlem yapılamadı: {error}",
        # ---------------- phases
        "phase.stopped": "DURDURULDU",
        "phase.waiting": "İNDİRME BEKLENİYOR",
        "phase.downloading": "İNDİRİLİYOR",
        "phase.draining": "TAMAMLANMA DOĞRULANIYOR",
        "phase.ready": "TAMAMLANDI",
        "phase.done": "İŞLEM UYGULANDI",
        "phase.interrupted": "İNDİRME KESİLDİ",
        # ---------------- banner details
        "detail.waiting": "Steam veya Epic'te bir indirme başlat — gerisini ben hallederim.",
        "detail.active": "{count} indirme sürüyor",
        "detail.active_others": "{count} izleniyor  ·  {others} yok sayıldı",
        "detail.nowatch": "Seçili indirme yok. İzlemek için bir oyunu işaretle.",
        "detail.draining": "Doğrulama için {seconds} sn kaldı",
        "detail.ready": "{seconds} sn sonra: {action}",
        "detail.stopped": "İzleme kapalı. \"İzlemeyi başlat\" düğmesine bas.",
        # ---------------- actions
        "action.shutdown": "Bilgisayarı kapat",
        "action.restart": "Yeniden başlat",
        "action.sleep": "Uyku moduna al",
        "action.hibernate": "Hazırda beklet",
        "action.test": "Test modu (kapatmaz)",
        # ---------------- row notes
        "row.on_disk": "diskte {size}",
        "row.queued": "sırada (başka bir indirme sürüyor)",
        "row.no_progress": "ilerleme bilgisi yok",
        # ---------------- units / relative time
        "unit.per_second": "/sn",
        "dur.seconds": "{s} sn",
        "dur.minutes": "{m} dk {s:02d} sn",
        "dur.hours": "{h} sa {m:02d} dk",
        "time.now": "şimdi",
        "time.sec_ago": "{n} sn önce",
        "time.min_ago": "{n} dk önce",
        "time.hour_ago": "{n} sa önce",
        # ---------------- event log
        "log.app_started": "AFK Game Downloader Pro başladı.",
        "log.steam_root": "Steam kökü: {path}",
        "log.steam_libs": "Steam kütüphaneleri: {paths}",
        "log.epic_found": "Epic: manifest klasörü bulundu",
        "log.epic_missing": "Epic: manifest klasörü bulunamadı (Epic kurulu olmayabilir)",
        "log.watching": "İzleme başladı. İndirme bekleniyor...",
        "log.stopped": "İzleme durduruldu.",
        "log.cancel_ok": "Kapatma iptal edildi. İzleme durduruldu.",
        "log.cancel_none": "İptal edilecek bir işlem yok; izleme durduruldu.",
        "log.download_detected": "İndirme algılandı: {names}",
        "log.tracking": "Takibe alındı: {name}",
        "log.drain_started": "İndirme durdu. {seconds} saniyelik doğrulama başladı...",
        "log.evidence": "Kanıt: {details}",
        "log.recheck_failed": "Son kontrol başarısız — işlem iptal edildi, tekrar doğrulanıyor.",
        "log.nothing_watched": "İşaretli indirme kalmadı — beklemeye dönüldü.",
        "log.interrupted_missing": "Steam indirme verisi kayboldu — indirme yarıda kesildi, izleme durduruldu.",
        "log.completed": "TAMAMLANDI: {names}",
        "log.action_in": "{seconds} sn sonra işlem: {action}",
        "log.resumed": "Yeni bir indirme başladı — kapatma iptal edildi.",
        "log.test_mode": "TEST MODU: '{action}' uygulanmadı (simüle edildi).",
        "log.executing": "İşlem uygulanıyor: {action}",
        "log.action_failed": "İşlem başarısız: {error}",
        "log.steam_scan_error": "Steam taraması hata verdi: {error}",
        "log.epic_scan_error": "Epic taraması hata verdi: {error}",
        "log.unexpected": "Beklenmeyen hata: {error}",
        "log.refresh": "Yenilendi: {active} indirme bulundu, {added} eklendi.",
        "log.new_download": "Listeye eklendi: {name}",
        "log.unwatched": "Yok sayıldı: {name}",
        # ---------------- verification reasons
        "verify.no_tracked": "takip edilen indirme yok",
        "verify.steam_rate": "Steam hâlâ indiriyor ({mbps:.1f} Mbps)",
        "verify.manifest_missing": "{name}: appmanifest bulunamadı",
        "verify.not_installed": "{name}: hâlâ tam kurulu değil (flags={flags})",
        "verify.log_state": "{name}: Steam günlüğündeki durum '{state}'",
        "verify.bytes_missing": "{name}: bayt eksik ({got} / {total})",
        "verify.epic_manifest_missing": "{name}: Epic manifest bulunamadı",
        "verify.epic_downloading": "{name}: Epic hâlâ indiriyor",
        "verify.unknown_source": "bilinmeyen kaynak: {key}",
        "verify.still_active": "{name} hâlâ aktif",
        "verify.ok": "tamam",
        # ---------------- kurulum sihirbazı
        "setup.title": "AFK Game Downloader Pro Kurulum",
        "setup.step": "Adım {current} / {total}",
        "setup.welcome_title": "AFK Game Downloader Pro'ya hoş geldin",
        "setup.welcome_body": (
            "Bu sihirbaz AFK Game Downloader Pro'yu bilgisayarına kuracak.\n\n"
            "Steam ve Epic Games indirmelerini izler, gerçekten bittiğinde "
            "bilgisayarı kapatır.\n\n"
            "Devam etmek için İleri'ye bas."
        ),
        "setup.lang_title": "Dil seçiniz",
        "setup.lang_body": "Kurulum ve uygulama için dili seç.",
        "setup.lang_hint": "Daha sonra programdan TR/EN düğmesiyle değiştirebilirsin.",
        "setup.license_title": "Lisans Sözleşmesi",
        "setup.license_body": "AFK Game Downloader Pro, MIT Lisansı ile yayınlanan özgür bir yazılımdır.",
        "setup.license_accept": "MIT Lisansı koşullarını kabul ediyorum",
        "setup.license_required": "Devam etmek için lisansı kabul et.",
        "setup.dest_title": "Kurulum konumunu seç",
        "setup.dest_body": (
            "Kurulum, AFK Game Downloader Pro'yu aşağıdaki klasöre kuracak.\n"
            "Sadece mevcut kullanıcı için kurulur, yönetici izni gerekmez."
        ),
        "setup.browse": "Gözat...",
        "setup.exists": "Burada mevcut bir kurulum var; güncellenecek.",
        "setup.tasks_title": "Ek görevler",
        "setup.tasks_body": "İstediğin kısayolları ve seçenekleri işaretle.",
        "setup.task_desktop": "Masaüstü kısayolu oluştur",
        "setup.task_startmenu": "Başlat menüsü kısayolu oluştur",
        "setup.ready_title": "Kuruluma hazır",
        "setup.ready_body": "Kurulum, AFK Game Downloader Pro'yu kurmaya hazır.",
        "setup.summary_dest": "Kurulum konumu",
        "setup.summary_tasks": "Görevler",
        "setup.none": "(yok)",
        "setup.installing_title": "Kuruluyor",
        "setup.installing_body": "Lütfen bekle, AFK Game Downloader Pro kuruluyor.",
        "setup.msg_prepare": "Hedef klasör hazırlanıyor...",
        "setup.msg_copy": "Uygulama dosyaları kopyalanıyor...",
        "setup.msg_shortcuts": "Kısayollar oluşturuluyor...",
        "setup.msg_register": "Uygulama kaydediliyor...",
        "setup.msg_uninstaller": "Kaldırma aracı yazılıyor...",
        "setup.msg_done": "Kurulum tamamlandı.",
        "setup.finish_title": "Kurulum tamamlandı",
        "setup.finish_body": "AFK Game Downloader Pro bilgisayarına kuruldu.",
        "setup.launch": "AFK Game Downloader Pro'yu başlat",
        "setup.btn_back": "Geri",
        "setup.btn_next": "İleri",
        "setup.btn_install": "Kur",
        "setup.btn_finish": "Bitir",
        "setup.btn_cancel": "İptal",
        "setup.err_title": "Kurulum başarısız",
        "setup.err_space": "Seçilen klasörde yeterli boş alan yok.",
        "setup.err_system": "Bu klasör Windows tarafından ayrılmış. Başka bir klasör seç.",
        "setup.err_exe_missing": "Paketlenmiş uygulama dosyası bulunamadı. Kurulumu yeniden derle.",
        "setup.cancel_title": "Kurulumu iptal et",
        "setup.cancel_body": "Kurulumdan çıkmak istiyor musun?",
        "setup.launch_failed": "Uygulama başlatılamadı: {error}",
        # ---------------- kaldırma sihirbazı
        "uninstall.title": "AFK Game Downloader Pro'yu Kaldır",
        "uninstall.heading": "AFK Game Downloader Pro bu bilgisayardan kaldırılsın mı?",
        "uninstall.body": "Şunlar silinecek:",
        "uninstall.item_app": "Uygulama ve dosyaları",
        "uninstall.item_shortcuts": "Masaüstü ve Başlat menüsü kısayolları",
        "uninstall.item_settings": "Ayarlar ve olay günlüğü",
        "uninstall.btn": "Kaldır",
        "uninstall.cancel": "İptal",
        "uninstall.progress": "Kaldırılıyor...",
        "uninstall.msg_stop": "Uygulama kapatılıyor...",
        "uninstall.msg_shortcuts": "Kısayollar siliniyor...",
        "uninstall.msg_registry": "Kayıt defteri temizleniyor...",
        "uninstall.msg_settings": "Ayarlar siliniyor...",
        "uninstall.msg_files": "Program dosyaları siliniyor...",
        "uninstall.msg_done": "Tamamlandı.",
        "uninstall.done_title": "AFK Game Downloader Pro kaldırıldı",
        "uninstall.done_body": "Uygulama, kısayolları ve kayıt defteri girdileri silindi.\nKalan klasör bu pencere kapandıktan birkaç saniye sonra silinir.",
        "uninstall.close": "Kapat",

        # ---------------- misc / shell
        "shell.already_running": "AFK Game Downloader Pro zaten çalışıyor.\nGörev çubuğundaki penceresini kontrol et.",
        "shell.crash": "AFK Game Downloader Pro beklenmedik bir hata ile durdu:\n\n{error}\n\nDetay: {path}",
    },
}

_current = DEFAULT_LANG


def get_lang() -> str:
    return _current


def set_lang(code: str) -> str:
    global _current
    code = (code or DEFAULT_LANG).lower()
    _current = code if code in STRINGS else DEFAULT_LANG
    return _current


def toggle_lang() -> str:
    return set_lang("tr" if _current == "en" else "en")


def tr(key: str, **params) -> str:
    """Translate ``key``; unknown keys fall back to English, then to the key itself."""
    table = STRINGS.get(_current, STRINGS[DEFAULT_LANG])
    text = table.get(key) or STRINGS[DEFAULT_LANG].get(key) or key
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            return text
    return text
