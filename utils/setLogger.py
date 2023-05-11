import logging.handlers
import os

class Setting():
    """로거 세팅 클래스
        ::
            Setting.LEVEL = logging.INFO # INFO 이상만 로그를 작성
    """
    LEVEL1 = logging.DEBUG
    LEVEL2 = logging.INFO
    MAX_BYTES = 10 * 1024 * 1024
    BACKUP_COUNT = 10
    FORMAT = "%(asctime)s[%(levelname)s|%(filename)s,%(lineno)s] %(message)s"


def Logger(name='log', logdir='./logs/', level='DEBUG'):
    """파일 로그 클래스
        :param name: 로그 이름
        :type name: str
        :return: 로거 인스턴스
        ::
            logger = Logger(__name__)
            logger.info('info 입니다')
    """

    # 로그폴더 없을 경우 폴더 생성
    os.makedirs(logdir, exist_ok=True)
    # 로거 & 포매터 & 핸들러 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 노말 상태 : LEVEL1, DEBUG
    formatter = logging.Formatter(Setting.FORMAT)  # 포맷 세팅

    # streamHandler = logging.StreamHandler()

    # fileHandler = logging.handlers.RotatingFileHandler(
    #     filename=logdir,
    #     maxBytes=Setting.MAX_BYTES,
    #     backupCount=Setting.BACKUP_COUNT)
    fileHandler = logging.handlers.TimedRotatingFileHandler(
        filename=logdir + '/' + name + '.log',
        encoding='utf-8', when='midnight', interval=1)

    ## stream(consle), file save level
    # streamHandler.setLevel(Setting.LEVEL2)
    if level == 'DEBUG':
        fileHandler.setLevel(Setting.LEVEL1)
    elif level == 'INFO':
        fileHandler.setLevel(Setting.LEVEL2)

    # 핸들러 & 포매터 결합
    # streamHandler.setFormatter(formatter)
    fileHandler.setFormatter(formatter)

    # 로거 & 핸들러 결합
    # logger.addHandler(streamHandler)
    logger.addHandler(fileHandler)

    # 로거 레벨 설정
    # logger.setLevel(Setting.LEVEL)

    return logger