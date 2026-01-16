"""
OBD-II Scanner Language Module
==============================
Multi-language support for the scanner interface.
Supported: English, Spanish, French, German, Portuguese, Italian
"""

from typing import Dict

LANGUAGES: Dict[str, Dict[str, str]] = {
    # =========================================================================
    # ENGLISH
    # =========================================================================
    "en": {
        # App info
        "app_name": "OBD-II Scanner",
        "version": "v2.0.0",
        
        # Main menu
        "main_menu": "MAIN MENU",
        "connect": "Connect to Vehicle",
        "disconnect": "Disconnect",
        "full_scan": "Full Diagnostic Scan",
        "read_codes": "Read Trouble Codes",
        "live_monitor": "Live Telemetry Monitor",
        "freeze_frame": "Freeze Frame Data",
        "readiness": "Readiness Monitors",
        "clear_codes": "Clear Codes",
        "lookup": "Lookup Code",
        "search": "Search Codes",
        "settings": "Settings",
        "exit": "Exit",
        "back": "Back to Main Menu",
        
        # Status
        "status": "Status",
        "connected": "Connected",
        "disconnected": "Disconnected",
        "vehicle": "Vehicle",
        "format": "Format",
        
        # Prompts
        "select_option": "Select option",
        "press_enter": "Press Enter to continue...",
        "confirm_yes_no": "Continue? (y/n)",
        "type_yes": "Type 'YES' to confirm",
        "cancelled": "Cancelled.",
        
        # Connection
        "connect_header": "CONNECT TO VEHICLE",
        "already_connected": "Already connected!",
        "disconnect_reconnect": "Disconnect and reconnect?",
        "searching_adapter": "Searching for OBD adapter...",
        "found_ports": "Found {count} port(s)",
        "trying_port": "Trying {port}...",
        "connected_on": "Connected on {port}",
        "connection_failed": "Failed: {error}",
        "no_ports_found": "No USB serial ports found!",
        "adapter_tip": "Make sure your ELM327 is plugged in.",
        "no_vehicle_response": "Could not connect to any vehicle.",
        "disconnected_at": "Disconnected at {time}",
        
        # Scan
        "scan_header": "FULL DIAGNOSTIC SCAN",
        "report_time": "Report Time",
        "vehicle_connection": "VEHICLE CONNECTION",
        "elm_version": "ELM327 Version",
        "protocol": "Protocol",
        "mil_status": "MIL (Check Engine)",
        "dtc_count": "DTC Count",
        
        # DTCs
        "dtc_header": "DIAGNOSTIC TROUBLE CODES",
        "no_codes": "No trouble codes stored",
        "code_lookup_header": "CODE LOOKUP",
        "enter_code": "Enter code (e.g., P0118)",
        "code_not_found": "Code '{code}' not found in database.",
        "similar_codes": "Similar codes:",
        "search_header": "SEARCH CODES",
        "search_prompt": "Search term (e.g., 'throttle', 'coolant')",
        "found_codes": "Found {count} codes:",
        "no_codes_found": "No codes found matching '{query}'",
        "codes_loaded": "codes loaded",
        "manufacturer": "Manufacturer",
        "source": "Source",
        
        # Live data
        "live_header": "LIVE SENSOR DATA",
        "live_telemetry": "LIVE TELEMETRY",
        "started": "Started",
        "refresh": "Refresh",
        "press_ctrl_c": "Press Ctrl+C to stop",
        "save_log_prompt": "Save to log file?",
        "logging_to": "Logging to",
        "time": "Time",
        "coolant": "Coolant",
        "speed": "Speed",
        "throttle": "Throttle",
        "pedal": "Pedal",
        "volts": "Volts",
        
        # Freeze frame
        "freeze_header": "FREEZE FRAME DATA",
        "no_freeze_data": "No freeze frame data available.",
        "freeze_tip": "(Freeze frames are captured when a DTC is stored)",
        "dtc_triggered": "DTC that triggered",
        
        # Readiness
        "readiness_header": "READINESS MONITORS",
        "unable_read_readiness": "Unable to read readiness monitors.",
        "complete": "Complete",
        "incomplete": "Incomplete",
        "not_available": "Not Available",
        "summary": "Summary",
        "readiness_tip": "Incomplete monitors need drive cycles to complete.",
        "readiness_tip2": "Normal after clearing codes or disconnecting battery.",
        
        # Clear codes
        "clear_header": "CLEAR TROUBLE CODES",
        "clear_warning": "WARNING: This will:",
        "clear_warn1": "Clear all stored DTCs",
        "clear_warn2": "Turn off Check Engine light",
        "clear_warn3": "Reset ALL readiness monitors",
        "clear_warn4": "Permanent codes will NOT be cleared",
        "clear_success": "DTCs cleared successfully at {time}",
        "clear_failed": "Failed to clear DTCs",
        
        # Settings
        "settings_header": "SETTINGS",
        "vehicle_make": "Vehicle Make",
        "log_format": "Log Format",
        "monitor_interval": "Monitor Interval",
        "view_ports": "View Serial Ports",
        "language": "Language",
        "available_manufacturers": "Available manufacturers:",
        "generic_all": "Generic (all codes)",
        "select_manufacturer": "Select",
        "set_to": "Set to {value}",
        "loaded_codes": "Loaded {count} codes",
        "log_formats": "Log formats:",
        "csv_desc": "CSV (spreadsheet compatible)",
        "json_desc": "JSON (structured data)",
        "current_interval": "Current interval: {value} seconds",
        "new_interval": "New interval (0.5 - 10)",
        "interval_set": "Interval set to {value}s",
        "invalid_range": "Must be between 0.5 and 10",
        "invalid_number": "Invalid number",
        "available_ports": "Available serial ports:",
        "no_ports": "No USB serial ports found",
        
        # Warnings
        "warning_high_temp": "HIGH - Possible overheating!",
        "warning_low_temp": "LOW - Engine not at operating temp",
        "warning_throttle": "Not fully closed at idle",
        "not_connected": "Not connected! Connect first.",
        
        # Session
        "session_summary": "Session Summary",
        "file": "File",
        "duration": "Duration",
        "seconds": "seconds",
        "readings": "Readings",
        
        # Misc
        "goodbye": "Goodbye!",
        "error": "Error",
        "yes": "yes",
        "no": "no",
        "on": "ON",
        "off": "OFF",
    },
    
    # =========================================================================
    # SPANISH (Español)
    # =========================================================================
    "es": {
        # App info
        "app_name": "Escáner OBD-II",
        "version": "v2.0.0",
        
        # Main menu
        "main_menu": "MENÚ PRINCIPAL",
        "connect": "Conectar al Vehículo",
        "disconnect": "Desconectar",
        "full_scan": "Escaneo Diagnóstico Completo",
        "read_codes": "Leer Códigos de Error",
        "live_monitor": "Monitor de Telemetría en Vivo",
        "freeze_frame": "Datos de Freeze Frame",
        "readiness": "Monitores de Preparación",
        "clear_codes": "Borrar Códigos",
        "lookup": "Buscar Código",
        "search": "Buscar en Base de Datos",
        "settings": "Configuración",
        "exit": "Salir",
        "back": "Volver al Menú Principal",
        
        # Status
        "status": "Estado",
        "connected": "Conectado",
        "disconnected": "Desconectado",
        "vehicle": "Vehículo",
        "format": "Formato",
        
        # Prompts
        "select_option": "Seleccione opción",
        "press_enter": "Presione Enter para continuar...",
        "confirm_yes_no": "¿Continuar? (s/n)",
        "type_yes": "Escriba 'SI' para confirmar",
        "cancelled": "Cancelado.",
        
        # Connection
        "connect_header": "CONECTAR AL VEHÍCULO",
        "already_connected": "¡Ya está conectado!",
        "disconnect_reconnect": "¿Desconectar y reconectar?",
        "searching_adapter": "Buscando adaptador OBD...",
        "found_ports": "Encontrado(s) {count} puerto(s)",
        "trying_port": "Probando {port}...",
        "connected_on": "Conectado en {port}",
        "connection_failed": "Falló: {error}",
        "no_ports_found": "¡No se encontraron puertos USB serial!",
        "adapter_tip": "Asegúrese de que su ELM327 está conectado.",
        "no_vehicle_response": "No se pudo conectar a ningún vehículo.",
        "disconnected_at": "Desconectado a las {time}",
        
        # Scan
        "scan_header": "ESCANEO DIAGNÓSTICO COMPLETO",
        "report_time": "Hora del Reporte",
        "vehicle_connection": "CONEXIÓN DEL VEHÍCULO",
        "elm_version": "Versión ELM327",
        "protocol": "Protocolo",
        "mil_status": "MIL (Check Engine)",
        "dtc_count": "Cantidad de DTCs",
        
        # DTCs
        "dtc_header": "CÓDIGOS DE DIAGNÓSTICO",
        "no_codes": "No hay códigos de error almacenados",
        "code_lookup_header": "BUSCAR CÓDIGO",
        "enter_code": "Ingrese código (ej: P0118)",
        "code_not_found": "Código '{code}' no encontrado en la base de datos.",
        "similar_codes": "Códigos similares:",
        "search_header": "BUSCAR CÓDIGOS",
        "search_prompt": "Término de búsqueda (ej: 'throttle', 'coolant')",
        "found_codes": "Encontrados {count} códigos:",
        "no_codes_found": "No se encontraron códigos para '{query}'",
        "codes_loaded": "códigos cargados",
        "manufacturer": "Fabricante",
        "source": "Fuente",
        
        # Live data
        "live_header": "DATOS DE SENSORES EN VIVO",
        "live_telemetry": "TELEMETRÍA EN VIVO",
        "started": "Iniciado",
        "refresh": "Actualización",
        "press_ctrl_c": "Presione Ctrl+C para detener",
        "save_log_prompt": "¿Guardar en archivo de log?",
        "logging_to": "Guardando en",
        "time": "Hora",
        "coolant": "Refrigerante",
        "speed": "Velocidad",
        "throttle": "Acelerador",
        "pedal": "Pedal",
        "volts": "Voltios",
        
        # Freeze frame
        "freeze_header": "DATOS DE FREEZE FRAME",
        "no_freeze_data": "No hay datos de freeze frame disponibles.",
        "freeze_tip": "(Los freeze frames se capturan cuando se almacena un DTC)",
        "dtc_triggered": "DTC que lo activó",
        
        # Readiness
        "readiness_header": "MONITORES DE PREPARACIÓN",
        "unable_read_readiness": "No se pudieron leer los monitores de preparación.",
        "complete": "Completo",
        "incomplete": "Incompleto",
        "not_available": "No Disponible",
        "summary": "Resumen",
        "readiness_tip": "Los monitores incompletos necesitan ciclos de manejo.",
        "readiness_tip2": "Normal después de borrar códigos o desconectar la batería.",
        
        # Clear codes
        "clear_header": "BORRAR CÓDIGOS DE ERROR",
        "clear_warning": "ADVERTENCIA: Esto hará:",
        "clear_warn1": "Borrar todos los DTCs almacenados",
        "clear_warn2": "Apagar la luz de Check Engine",
        "clear_warn3": "Resetear TODOS los monitores de preparación",
        "clear_warn4": "Los códigos permanentes NO se borrarán",
        "clear_success": "DTCs borrados exitosamente a las {time}",
        "clear_failed": "Error al borrar DTCs",
        
        # Settings
        "settings_header": "CONFIGURACIÓN",
        "vehicle_make": "Marca del Vehículo",
        "log_format": "Formato de Log",
        "monitor_interval": "Intervalo de Monitor",
        "view_ports": "Ver Puertos Serial",
        "language": "Idioma",
        "available_manufacturers": "Fabricantes disponibles:",
        "generic_all": "Genérico (todos los códigos)",
        "select_manufacturer": "Seleccione",
        "set_to": "Configurado a {value}",
        "loaded_codes": "Cargados {count} códigos",
        "log_formats": "Formatos de log:",
        "csv_desc": "CSV (compatible con hojas de cálculo)",
        "json_desc": "JSON (datos estructurados)",
        "current_interval": "Intervalo actual: {value} segundos",
        "new_interval": "Nuevo intervalo (0.5 - 10)",
        "interval_set": "Intervalo configurado a {value}s",
        "invalid_range": "Debe estar entre 0.5 y 10",
        "invalid_number": "Número inválido",
        "available_ports": "Puertos serial disponibles:",
        "no_ports": "No se encontraron puertos USB serial",
        
        # Warnings
        "warning_high_temp": "ALTO - ¡Posible sobrecalentamiento!",
        "warning_low_temp": "BAJO - Motor no está a temperatura de operación",
        "warning_throttle": "No está completamente cerrado en ralentí",
        "not_connected": "¡No conectado! Conecte primero.",
        
        # Session
        "session_summary": "Resumen de Sesión",
        "file": "Archivo",
        "duration": "Duración",
        "seconds": "segundos",
        "readings": "Lecturas",
        
        # Misc
        "goodbye": "¡Hasta luego!",
        "error": "Error",
        "yes": "sí",
        "no": "no",
        "on": "ENCENDIDO",
        "off": "APAGADO",
    },
    
    # =========================================================================
    # FRENCH (Français)
    # =========================================================================
    "fr": {
        # App info
        "app_name": "Scanner OBD-II",
        "version": "v2.0.0",
        
        # Main menu
        "main_menu": "MENU PRINCIPAL",
        "connect": "Connecter au Véhicule",
        "disconnect": "Déconnecter",
        "full_scan": "Diagnostic Complet",
        "read_codes": "Lire les Codes d'Erreur",
        "live_monitor": "Télémétrie en Direct",
        "freeze_frame": "Données Freeze Frame",
        "readiness": "Moniteurs de Préparation",
        "clear_codes": "Effacer les Codes",
        "lookup": "Rechercher un Code",
        "search": "Rechercher dans la Base",
        "settings": "Paramètres",
        "exit": "Quitter",
        "back": "Retour au Menu Principal",
        
        # Status
        "status": "Statut",
        "connected": "Connecté",
        "disconnected": "Déconnecté",
        "vehicle": "Véhicule",
        "format": "Format",
        
        # Prompts
        "select_option": "Sélectionnez une option",
        "press_enter": "Appuyez sur Entrée pour continuer...",
        "confirm_yes_no": "Continuer? (o/n)",
        "type_yes": "Tapez 'OUI' pour confirmer",
        "cancelled": "Annulé.",
        
        # Connection
        "connect_header": "CONNECTER AU VÉHICULE",
        "already_connected": "Déjà connecté!",
        "disconnect_reconnect": "Déconnecter et reconnecter?",
        "searching_adapter": "Recherche de l'adaptateur OBD...",
        "found_ports": "{count} port(s) trouvé(s)",
        "trying_port": "Essai de {port}...",
        "connected_on": "Connecté sur {port}",
        "connection_failed": "Échec: {error}",
        "no_ports_found": "Aucun port série USB trouvé!",
        "adapter_tip": "Assurez-vous que votre ELM327 est branché.",
        "no_vehicle_response": "Impossible de se connecter à un véhicule.",
        "disconnected_at": "Déconnecté à {time}",
        
        # Scan
        "scan_header": "DIAGNOSTIC COMPLET",
        "report_time": "Heure du Rapport",
        "vehicle_connection": "CONNEXION VÉHICULE",
        "elm_version": "Version ELM327",
        "protocol": "Protocole",
        "mil_status": "MIL (Voyant Moteur)",
        "dtc_count": "Nombre de DTCs",
        
        # DTCs
        "dtc_header": "CODES DE DIAGNOSTIC",
        "no_codes": "Aucun code d'erreur enregistré",
        "code_lookup_header": "RECHERCHER UN CODE",
        "enter_code": "Entrez le code (ex: P0118)",
        "code_not_found": "Code '{code}' non trouvé dans la base de données.",
        "similar_codes": "Codes similaires:",
        "search_header": "RECHERCHER DES CODES",
        "search_prompt": "Terme de recherche (ex: 'throttle', 'coolant')",
        "found_codes": "{count} codes trouvés:",
        "no_codes_found": "Aucun code trouvé pour '{query}'",
        "codes_loaded": "codes chargés",
        "manufacturer": "Fabricant",
        "source": "Source",
        
        # Live data
        "live_header": "DONNÉES CAPTEURS EN DIRECT",
        "live_telemetry": "TÉLÉMÉTRIE EN DIRECT",
        "started": "Démarré",
        "refresh": "Actualisation",
        "press_ctrl_c": "Appuyez sur Ctrl+C pour arrêter",
        "save_log_prompt": "Enregistrer dans un fichier?",
        "logging_to": "Enregistrement dans",
        "time": "Heure",
        "coolant": "Liquide Refroid.",
        "speed": "Vitesse",
        "throttle": "Papillon",
        "pedal": "Pédale",
        "volts": "Volts",
        
        # Freeze frame
        "freeze_header": "DONNÉES FREEZE FRAME",
        "no_freeze_data": "Aucune donnée freeze frame disponible.",
        "freeze_tip": "(Les freeze frames sont capturés lors de l'enregistrement d'un DTC)",
        "dtc_triggered": "DTC déclencheur",
        
        # Readiness
        "readiness_header": "MONITEURS DE PRÉPARATION",
        "unable_read_readiness": "Impossible de lire les moniteurs de préparation.",
        "complete": "Terminé",
        "incomplete": "Incomplet",
        "not_available": "Non Disponible",
        "summary": "Résumé",
        "readiness_tip": "Les moniteurs incomplets nécessitent des cycles de conduite.",
        "readiness_tip2": "Normal après effacement des codes ou déconnexion batterie.",
        
        # Clear codes
        "clear_header": "EFFACER LES CODES D'ERREUR",
        "clear_warning": "ATTENTION: Ceci va:",
        "clear_warn1": "Effacer tous les DTCs enregistrés",
        "clear_warn2": "Éteindre le voyant moteur",
        "clear_warn3": "Réinitialiser TOUS les moniteurs de préparation",
        "clear_warn4": "Les codes permanents NE seront PAS effacés",
        "clear_success": "DTCs effacés avec succès à {time}",
        "clear_failed": "Échec de l'effacement des DTCs",
        
        # Settings
        "settings_header": "PARAMÈTRES",
        "vehicle_make": "Marque du Véhicule",
        "log_format": "Format de Log",
        "monitor_interval": "Intervalle du Moniteur",
        "view_ports": "Voir les Ports Série",
        "language": "Langue",
        "available_manufacturers": "Fabricants disponibles:",
        "generic_all": "Générique (tous les codes)",
        "select_manufacturer": "Sélectionnez",
        "set_to": "Défini sur {value}",
        "loaded_codes": "{count} codes chargés",
        "log_formats": "Formats de log:",
        "csv_desc": "CSV (compatible tableur)",
        "json_desc": "JSON (données structurées)",
        "current_interval": "Intervalle actuel: {value} secondes",
        "new_interval": "Nouvel intervalle (0.5 - 10)",
        "interval_set": "Intervalle défini à {value}s",
        "invalid_range": "Doit être entre 0.5 et 10",
        "invalid_number": "Nombre invalide",
        "available_ports": "Ports série disponibles:",
        "no_ports": "Aucun port série USB trouvé",
        
        # Warnings
        "warning_high_temp": "ÉLEVÉ - Surchauffe possible!",
        "warning_low_temp": "BAS - Moteur pas à température",
        "warning_throttle": "Pas complètement fermé au ralenti",
        "not_connected": "Non connecté! Connectez d'abord.",
        
        # Session
        "session_summary": "Résumé de Session",
        "file": "Fichier",
        "duration": "Durée",
        "seconds": "secondes",
        "readings": "Lectures",
        
        # Misc
        "goodbye": "Au revoir!",
        "error": "Erreur",
        "yes": "oui",
        "no": "non",
        "on": "ALLUMÉ",
        "off": "ÉTEINT",
    },
    
    # =========================================================================
    # GERMAN (Deutsch)
    # =========================================================================
    "de": {
        # App info
        "app_name": "OBD-II Scanner",
        "version": "v2.0.0",
        
        # Main menu
        "main_menu": "HAUPTMENÜ",
        "connect": "Mit Fahrzeug verbinden",
        "disconnect": "Trennen",
        "full_scan": "Vollständige Diagnose",
        "read_codes": "Fehlercodes lesen",
        "live_monitor": "Live-Telemetrie",
        "freeze_frame": "Freeze Frame Daten",
        "readiness": "Bereitschaftsmonitore",
        "clear_codes": "Codes löschen",
        "lookup": "Code nachschlagen",
        "search": "Codes suchen",
        "settings": "Einstellungen",
        "exit": "Beenden",
        "back": "Zurück zum Hauptmenü",
        
        # Status
        "status": "Status",
        "connected": "Verbunden",
        "disconnected": "Getrennt",
        "vehicle": "Fahrzeug",
        "format": "Format",
        
        # Prompts
        "select_option": "Option wählen",
        "press_enter": "Drücken Sie Enter zum Fortfahren...",
        "confirm_yes_no": "Fortfahren? (j/n)",
        "type_yes": "Geben Sie 'JA' zur Bestätigung ein",
        "cancelled": "Abgebrochen.",
        
        # Connection
        "connect_header": "MIT FAHRZEUG VERBINDEN",
        "already_connected": "Bereits verbunden!",
        "disconnect_reconnect": "Trennen und neu verbinden?",
        "searching_adapter": "Suche OBD-Adapter...",
        "found_ports": "{count} Port(s) gefunden",
        "trying_port": "Versuche {port}...",
        "connected_on": "Verbunden auf {port}",
        "connection_failed": "Fehlgeschlagen: {error}",
        "no_ports_found": "Keine USB-Serial-Ports gefunden!",
        "adapter_tip": "Stellen Sie sicher, dass Ihr ELM327 angeschlossen ist.",
        "no_vehicle_response": "Konnte keine Verbindung zum Fahrzeug herstellen.",
        "disconnected_at": "Getrennt um {time}",
        
        # Scan
        "scan_header": "VOLLSTÄNDIGE DIAGNOSE",
        "report_time": "Berichtszeit",
        "vehicle_connection": "FAHRZEUGVERBINDUNG",
        "elm_version": "ELM327 Version",
        "protocol": "Protokoll",
        "mil_status": "MIL (Motorleuchte)",
        "dtc_count": "Anzahl DTCs",
        
        # DTCs
        "dtc_header": "DIAGNOSE-FEHLERCODES",
        "no_codes": "Keine Fehlercodes gespeichert",
        "code_lookup_header": "CODE NACHSCHLAGEN",
        "enter_code": "Code eingeben (z.B. P0118)",
        "code_not_found": "Code '{code}' nicht in Datenbank gefunden.",
        "similar_codes": "Ähnliche Codes:",
        "search_header": "CODES SUCHEN",
        "search_prompt": "Suchbegriff (z.B. 'throttle', 'coolant')",
        "found_codes": "{count} Codes gefunden:",
        "no_codes_found": "Keine Codes für '{query}' gefunden",
        "codes_loaded": "Codes geladen",
        "manufacturer": "Hersteller",
        "source": "Quelle",
        
        # Live data
        "live_header": "LIVE-SENSORDATEN",
        "live_telemetry": "LIVE-TELEMETRIE",
        "started": "Gestartet",
        "refresh": "Aktualisierung",
        "press_ctrl_c": "Drücken Sie Strg+C zum Stoppen",
        "save_log_prompt": "In Datei speichern?",
        "logging_to": "Speichere in",
        "time": "Zeit",
        "coolant": "Kühlmittel",
        "speed": "Geschwindigkeit",
        "throttle": "Drosselklappe",
        "pedal": "Pedal",
        "volts": "Volt",
        
        # Freeze frame
        "freeze_header": "FREEZE FRAME DATEN",
        "no_freeze_data": "Keine Freeze Frame Daten verfügbar.",
        "freeze_tip": "(Freeze Frames werden bei DTC-Speicherung aufgezeichnet)",
        "dtc_triggered": "Auslösender DTC",
        
        # Readiness
        "readiness_header": "BEREITSCHAFTSMONITORE",
        "unable_read_readiness": "Bereitschaftsmonitore konnten nicht gelesen werden.",
        "complete": "Abgeschlossen",
        "incomplete": "Unvollständig",
        "not_available": "Nicht Verfügbar",
        "summary": "Zusammenfassung",
        "readiness_tip": "Unvollständige Monitore benötigen Fahrzyklen.",
        "readiness_tip2": "Normal nach Löschen der Codes oder Batterietrennung.",
        
        # Clear codes
        "clear_header": "FEHLERCODES LÖSCHEN",
        "clear_warning": "WARNUNG: Dies wird:",
        "clear_warn1": "Alle gespeicherten DTCs löschen",
        "clear_warn2": "Motorleuchte ausschalten",
        "clear_warn3": "ALLE Bereitschaftsmonitore zurücksetzen",
        "clear_warn4": "Permanente Codes werden NICHT gelöscht",
        "clear_success": "DTCs erfolgreich gelöscht um {time}",
        "clear_failed": "Löschen der DTCs fehlgeschlagen",
        
        # Settings
        "settings_header": "EINSTELLUNGEN",
        "vehicle_make": "Fahrzeugmarke",
        "log_format": "Log-Format",
        "monitor_interval": "Monitor-Intervall",
        "view_ports": "Serial-Ports anzeigen",
        "language": "Sprache",
        "available_manufacturers": "Verfügbare Hersteller:",
        "generic_all": "Generisch (alle Codes)",
        "select_manufacturer": "Auswählen",
        "set_to": "Eingestellt auf {value}",
        "loaded_codes": "{count} Codes geladen",
        "log_formats": "Log-Formate:",
        "csv_desc": "CSV (Tabellenkalkulation kompatibel)",
        "json_desc": "JSON (strukturierte Daten)",
        "current_interval": "Aktuelles Intervall: {value} Sekunden",
        "new_interval": "Neues Intervall (0.5 - 10)",
        "interval_set": "Intervall auf {value}s eingestellt",
        "invalid_range": "Muss zwischen 0.5 und 10 liegen",
        "invalid_number": "Ungültige Zahl",
        "available_ports": "Verfügbare Serial-Ports:",
        "no_ports": "Keine USB-Serial-Ports gefunden",
        
        # Warnings
        "warning_high_temp": "HOCH - Mögliche Überhitzung!",
        "warning_low_temp": "NIEDRIG - Motor nicht auf Betriebstemperatur",
        "warning_throttle": "Nicht vollständig geschlossen im Leerlauf",
        "not_connected": "Nicht verbunden! Zuerst verbinden.",
        
        # Session
        "session_summary": "Sitzungszusammenfassung",
        "file": "Datei",
        "duration": "Dauer",
        "seconds": "Sekunden",
        "readings": "Messwerte",
        
        # Misc
        "goodbye": "Auf Wiedersehen!",
        "error": "Fehler",
        "yes": "ja",
        "no": "nein",
        "on": "EIN",
        "off": "AUS",
    },
    
    # =========================================================================
    # PORTUGUESE (Português)
    # =========================================================================
    "pt": {
        # App info
        "app_name": "Scanner OBD-II",
        "version": "v2.0.0",
        
        # Main menu
        "main_menu": "MENU PRINCIPAL",
        "connect": "Conectar ao Veículo",
        "disconnect": "Desconectar",
        "full_scan": "Diagnóstico Completo",
        "read_codes": "Ler Códigos de Erro",
        "live_monitor": "Monitor de Telemetria ao Vivo",
        "freeze_frame": "Dados de Freeze Frame",
        "readiness": "Monitores de Prontidão",
        "clear_codes": "Apagar Códigos",
        "lookup": "Buscar Código",
        "search": "Pesquisar Códigos",
        "settings": "Configurações",
        "exit": "Sair",
        "back": "Voltar ao Menu Principal",
        
        # Status
        "status": "Status",
        "connected": "Conectado",
        "disconnected": "Desconectado",
        "vehicle": "Veículo",
        "format": "Formato",
        
        # Prompts
        "select_option": "Selecione uma opção",
        "press_enter": "Pressione Enter para continuar...",
        "confirm_yes_no": "Continuar? (s/n)",
        "type_yes": "Digite 'SIM' para confirmar",
        "cancelled": "Cancelado.",
        
        # Connection
        "connect_header": "CONECTAR AO VEÍCULO",
        "already_connected": "Já está conectado!",
        "disconnect_reconnect": "Desconectar e reconectar?",
        "searching_adapter": "Procurando adaptador OBD...",
        "found_ports": "{count} porta(s) encontrada(s)",
        "trying_port": "Tentando {port}...",
        "connected_on": "Conectado em {port}",
        "connection_failed": "Falhou: {error}",
        "no_ports_found": "Nenhuma porta serial USB encontrada!",
        "adapter_tip": "Certifique-se de que seu ELM327 está conectado.",
        "no_vehicle_response": "Não foi possível conectar a nenhum veículo.",
        "disconnected_at": "Desconectado às {time}",
        
        # Scan
        "scan_header": "DIAGNÓSTICO COMPLETO",
        "report_time": "Hora do Relatório",
        "vehicle_connection": "CONEXÃO DO VEÍCULO",
        "elm_version": "Versão ELM327",
        "protocol": "Protocolo",
        "mil_status": "MIL (Luz do Motor)",
        "dtc_count": "Quantidade de DTCs",
        
        # DTCs
        "dtc_header": "CÓDIGOS DE DIAGNÓSTICO",
        "no_codes": "Nenhum código de erro armazenado",
        "code_lookup_header": "BUSCAR CÓDIGO",
        "enter_code": "Digite o código (ex: P0118)",
        "code_not_found": "Código '{code}' não encontrado no banco de dados.",
        "similar_codes": "Códigos similares:",
        "search_header": "PESQUISAR CÓDIGOS",
        "search_prompt": "Termo de pesquisa (ex: 'throttle', 'coolant')",
        "found_codes": "{count} códigos encontrados:",
        "no_codes_found": "Nenhum código encontrado para '{query}'",
        "codes_loaded": "códigos carregados",
        "manufacturer": "Fabricante",
        "source": "Fonte",
        
        # Live data
        "live_header": "DADOS DOS SENSORES AO VIVO",
        "live_telemetry": "TELEMETRIA AO VIVO",
        "started": "Iniciado",
        "refresh": "Atualização",
        "press_ctrl_c": "Pressione Ctrl+C para parar",
        "save_log_prompt": "Salvar em arquivo de log?",
        "logging_to": "Salvando em",
        "time": "Hora",
        "coolant": "Refrigerante",
        "speed": "Velocidade",
        "throttle": "Acelerador",
        "pedal": "Pedal",
        "volts": "Volts",
        
        # Freeze frame
        "freeze_header": "DADOS DE FREEZE FRAME",
        "no_freeze_data": "Nenhum dado de freeze frame disponível.",
        "freeze_tip": "(Freeze frames são capturados quando um DTC é armazenado)",
        "dtc_triggered": "DTC que ativou",
        
        # Readiness
        "readiness_header": "MONITORES DE PRONTIDÃO",
        "unable_read_readiness": "Não foi possível ler os monitores de prontidão.",
        "complete": "Completo",
        "incomplete": "Incompleto",
        "not_available": "Não Disponível",
        "summary": "Resumo",
        "readiness_tip": "Monitores incompletos precisam de ciclos de direção.",
        "readiness_tip2": "Normal após apagar códigos ou desconectar a bateria.",
        
        # Clear codes
        "clear_header": "APAGAR CÓDIGOS DE ERRO",
        "clear_warning": "AVISO: Isto irá:",
        "clear_warn1": "Apagar todos os DTCs armazenados",
        "clear_warn2": "Apagar a luz do motor",
        "clear_warn3": "Resetar TODOS os monitores de prontidão",
        "clear_warn4": "Códigos permanentes NÃO serão apagados",
        "clear_success": "DTCs apagados com sucesso às {time}",
        "clear_failed": "Falha ao apagar DTCs",
        
        # Settings
        "settings_header": "CONFIGURAÇÕES",
        "vehicle_make": "Marca do Veículo",
        "log_format": "Formato de Log",
        "monitor_interval": "Intervalo do Monitor",
        "view_ports": "Ver Portas Serial",
        "language": "Idioma",
        "available_manufacturers": "Fabricantes disponíveis:",
        "generic_all": "Genérico (todos os códigos)",
        "select_manufacturer": "Selecione",
        "set_to": "Configurado para {value}",
        "loaded_codes": "{count} códigos carregados",
        "log_formats": "Formatos de log:",
        "csv_desc": "CSV (compatível com planilhas)",
        "json_desc": "JSON (dados estruturados)",
        "current_interval": "Intervalo atual: {value} segundos",
        "new_interval": "Novo intervalo (0.5 - 10)",
        "interval_set": "Intervalo configurado para {value}s",
        "invalid_range": "Deve estar entre 0.5 e 10",
        "invalid_number": "Número inválido",
        "available_ports": "Portas serial disponíveis:",
        "no_ports": "Nenhuma porta serial USB encontrada",
        
        # Warnings
        "warning_high_temp": "ALTO - Possível superaquecimento!",
        "warning_low_temp": "BAIXO - Motor não está na temperatura de operação",
        "warning_throttle": "Não está completamente fechado em marcha lenta",
        "not_connected": "Não conectado! Conecte primeiro.",
        
        # Session
        "session_summary": "Resumo da Sessão",
        "file": "Arquivo",
        "duration": "Duração",
        "seconds": "segundos",
        "readings": "Leituras",
        
        # Misc
        "goodbye": "Até logo!",
        "error": "Erro",
        "yes": "sim",
        "no": "não",
        "on": "LIGADO",
        "off": "DESLIGADO",
    },
    
    # =========================================================================
    # ITALIAN (Italiano)
    # =========================================================================
    "it": {
        # App info
        "app_name": "Scanner OBD-II",
        "version": "v2.0.0",
        
        # Main menu
        "main_menu": "MENU PRINCIPALE",
        "connect": "Connetti al Veicolo",
        "disconnect": "Disconnetti",
        "full_scan": "Diagnosi Completa",
        "read_codes": "Leggi Codici Errore",
        "live_monitor": "Telemetria in Tempo Reale",
        "freeze_frame": "Dati Freeze Frame",
        "readiness": "Monitor di Prontezza",
        "clear_codes": "Cancella Codici",
        "lookup": "Cerca Codice",
        "search": "Cerca nel Database",
        "settings": "Impostazioni",
        "exit": "Esci",
        "back": "Torna al Menu Principale",
        
        # Status
        "status": "Stato",
        "connected": "Connesso",
        "disconnected": "Disconnesso",
        "vehicle": "Veicolo",
        "format": "Formato",
        
        # Prompts
        "select_option": "Seleziona opzione",
        "press_enter": "Premi Invio per continuare...",
        "confirm_yes_no": "Continuare? (s/n)",
        "type_yes": "Digita 'SI' per confermare",
        "cancelled": "Annullato.",
        
        # Connection
        "connect_header": "CONNETTI AL VEICOLO",
        "already_connected": "Già connesso!",
        "disconnect_reconnect": "Disconnettere e riconnettere?",
        "searching_adapter": "Ricerca adattatore OBD...",
        "found_ports": "{count} porta/e trovata/e",
        "trying_port": "Provo {port}...",
        "connected_on": "Connesso su {port}",
        "connection_failed": "Fallito: {error}",
        "no_ports_found": "Nessuna porta seriale USB trovata!",
        "adapter_tip": "Assicurati che il tuo ELM327 sia collegato.",
        "no_vehicle_response": "Impossibile connettersi a qualsiasi veicolo.",
        "disconnected_at": "Disconnesso alle {time}",
        
        # Scan
        "scan_header": "DIAGNOSI COMPLETA",
        "report_time": "Ora del Rapporto",
        "vehicle_connection": "CONNESSIONE VEICOLO",
        "elm_version": "Versione ELM327",
        "protocol": "Protocollo",
        "mil_status": "MIL (Spia Motore)",
        "dtc_count": "Numero DTCs",
        
        # DTCs
        "dtc_header": "CODICI DI DIAGNOSI",
        "no_codes": "Nessun codice errore memorizzato",
        "code_lookup_header": "CERCA CODICE",
        "enter_code": "Inserisci codice (es: P0118)",
        "code_not_found": "Codice '{code}' non trovato nel database.",
        "similar_codes": "Codici simili:",
        "search_header": "CERCA CODICI",
        "search_prompt": "Termine di ricerca (es: 'throttle', 'coolant')",
        "found_codes": "{count} codici trovati:",
        "no_codes_found": "Nessun codice trovato per '{query}'",
        "codes_loaded": "codici caricati",
        "manufacturer": "Produttore",
        "source": "Fonte",
        
        # Live data
        "live_header": "DATI SENSORI IN TEMPO REALE",
        "live_telemetry": "TELEMETRIA IN TEMPO REALE",
        "started": "Avviato",
        "refresh": "Aggiornamento",
        "press_ctrl_c": "Premi Ctrl+C per fermare",
        "save_log_prompt": "Salvare su file di log?",
        "logging_to": "Salvataggio in",
        "time": "Ora",
        "coolant": "Refrigerante",
        "speed": "Velocità",
        "throttle": "Acceleratore",
        "pedal": "Pedale",
        "volts": "Volt",
        
        # Freeze frame
        "freeze_header": "DATI FREEZE FRAME",
        "no_freeze_data": "Nessun dato freeze frame disponibile.",
        "freeze_tip": "(I freeze frame vengono catturati quando viene memorizzato un DTC)",
        "dtc_triggered": "DTC che ha attivato",
        
        # Readiness
        "readiness_header": "MONITOR DI PRONTEZZA",
        "unable_read_readiness": "Impossibile leggere i monitor di prontezza.",
        "complete": "Completo",
        "incomplete": "Incompleto",
        "not_available": "Non Disponibile",
        "summary": "Riepilogo",
        "readiness_tip": "I monitor incompleti necessitano di cicli di guida.",
        "readiness_tip2": "Normale dopo aver cancellato i codici o scollegato la batteria.",
        
        # Clear codes
        "clear_header": "CANCELLA CODICI ERRORE",
        "clear_warning": "ATTENZIONE: Questo:",
        "clear_warn1": "Cancellerà tutti i DTC memorizzati",
        "clear_warn2": "Spegnerà la spia del motore",
        "clear_warn3": "Resetterà TUTTI i monitor di prontezza",
        "clear_warn4": "I codici permanenti NON saranno cancellati",
        "clear_success": "DTCs cancellati con successo alle {time}",
        "clear_failed": "Cancellazione DTCs fallita",
        
        # Settings
        "settings_header": "IMPOSTAZIONI",
        "vehicle_make": "Marca del Veicolo",
        "log_format": "Formato Log",
        "monitor_interval": "Intervallo Monitor",
        "view_ports": "Visualizza Porte Seriali",
        "language": "Lingua",
        "available_manufacturers": "Produttori disponibili:",
        "generic_all": "Generico (tutti i codici)",
        "select_manufacturer": "Seleziona",
        "set_to": "Impostato su {value}",
        "loaded_codes": "{count} codici caricati",
        "log_formats": "Formati log:",
        "csv_desc": "CSV (compatibile con fogli di calcolo)",
        "json_desc": "JSON (dati strutturati)",
        "current_interval": "Intervallo attuale: {value} secondi",
        "new_interval": "Nuovo intervallo (0.5 - 10)",
        "interval_set": "Intervallo impostato a {value}s",
        "invalid_range": "Deve essere tra 0.5 e 10",
        "invalid_number": "Numero non valido",
        "available_ports": "Porte seriali disponibili:",
        "no_ports": "Nessuna porta seriale USB trovata",
        
        # Warnings
        "warning_high_temp": "ALTO - Possibile surriscaldamento!",
        "warning_low_temp": "BASSO - Motore non a temperatura di esercizio",
        "warning_throttle": "Non completamente chiuso al minimo",
        "not_connected": "Non connesso! Connetti prima.",
        
        # Session
        "session_summary": "Riepilogo Sessione",
        "file": "File",
        "duration": "Durata",
        "seconds": "secondi",
        "readings": "Letture",
        
        # Misc
        "goodbye": "Arrivederci!",
        "error": "Errore",
        "yes": "sì",
        "no": "no",
        "on": "ACCESO",
        "off": "SPENTO",
    },
}

# =============================================================================
# Language Helper Functions
# =============================================================================

# Current language (default: English)
_current_language: str = "en"


def get_language() -> str:
    """Get current language code."""
    return _current_language


def set_language(lang_code: str) -> bool:
    """
    Set current language.
    
    Args:
        lang_code: Language code (en, es, fr, de, pt, it)
        
    Returns:
        True if language was set, False if invalid code
    """
    global _current_language
    
    if lang_code.lower() in LANGUAGES:
        _current_language = lang_code.lower()
        return True
    return False


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.
    
    Args:
        key: Translation key
        **kwargs: Format arguments (e.g., count=5, time="12:00")
        
    Returns:
        Translated string, or the key itself if not found
    """
    lang_dict = LANGUAGES.get(_current_language, LANGUAGES["en"])
    text = lang_dict.get(key, LANGUAGES["en"].get(key, key))
    
    # Apply format arguments if any
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    
    return text


def get_available_languages() -> dict:
    """Get dictionary of available language codes and names."""
    return {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "pt": "Português",
        "it": "Italiano",
    }


def get_language_name(code: str) -> str:
    """Get the display name for a language code."""
    names = get_available_languages()
    return names.get(code, code)
