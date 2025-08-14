import os
import jaydebeapi
from ..config import JAR_PATH, IBMI_HOST, IBMI_USER, IBMI_PASSWORD


def connect_ibmi():
    if not os.path.exists(JAR_PATH):
        raise FileNotFoundError(f"No se encontró jt400.jar en: {JAR_PATH}")
    url = f"jdbc:as400://{IBMI_HOST}"
    return jaydebeapi.connect(
        "com.ibm.as400.access.AS400JDBCDriver",
        url,
        [IBMI_USER, IBMI_PASSWORD],
        JAR_PATH,
    )
