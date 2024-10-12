from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    SLEEP_TIME: list[int] = [300, 500]
    START_DELAY: list[int] = [25, 55]
    MAX_COMBO_COUNT: int = 28
    AUTO_TASK: bool = True
    REF_ID: str = "134115058"
    RANDOM_PREDICTION: bool = True
    FUEL_TANK_BOOST: bool = True
    RELOAD_TANK_BOOST: bool = True
    TURBO_CHARGER_BOOST: bool = True
    USE_PROXY_FROM_FILE: bool = False


settings = Settings()


