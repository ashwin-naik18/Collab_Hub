import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') 

    DB_CONFIG = {
        'host':     os.environ.get('DB_HOST'),
        'user':     os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD') ,
        'database': os.environ.get('DB_NAME'),
        'charset':  'utf8mb4',
        'autocommit': True
    }

    MAIL_SERVER         = os.environ.get('MAIL_SERVER') 
    MAIL_PORT           = int(os.environ.get('MAIL_PORT') )
    MAIL_USE_TLS        = os.environ.get('MAIL_USE_TLS',  'True').lower()  == 'true'
    MAIL_USE_SSL        = os.environ.get('MAIL_USE_SSL',  'False').lower() == 'true'
    MAIL_USERNAME       = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD') 
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME') 

    OTP_EXPIRY_MINUTES = 5
    OTP_LENGTH         = 6

    PERMANENT_SESSION_LIFETIME = 86400   
    SESSION_COOKIE_SECURE      = False   
    SESSION_COOKIE_HTTPONLY    = True
    SESSION_COOKIE_SAMESITE    = 'Lax'

    IDEAS_PER_PAGE = 12
