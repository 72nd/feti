import typed_settings as ts


@ts.settings
class Settings:
    port: int
    """Port for the web-server"""
    proxy_headers: bool
    """Whether Uvicorn should provide proxy headers"""
    nocodb_url: str
    """URL of NocoDB instance."""
    nocodb_org_name: str
    """Org name of NocoDB, most of the time `noco`."""
    project_name: str
    """Name of the NocoDB project."""
    log_level: str
    """Logging level for the application."""
    table_timetable: str
    table_entries: str
    table_location: str
    column_timetable_when: str
    column_timetable_entry: str
    column_entries_artist_name: str
    column_entries_title: str
    column_entries_genre: str
    column_entries_description: str
    column_entries_artist_cv: str
    column_entries_location: str
    column_location_name: str
    dev_mode: bool
    """
    Whether application should run in development mode or not. This currently only enables
    Uvicorn's auto reload.
    """
    title: str
    """Title of the site."""
    description: str
    """Description of the site."""
    nocodb_api_key: str = ts.secret()
    """API Key for the NocoDB instance."""


settings = ts.load(Settings, appname="feti", config_files=["settings.toml", ".secrets.toml"])