"""
core/sms.py
===========
Cliente SMS para Moçambique via Africa's Talking.
"""

import re
import logging
from django.conf import settings
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Validação de números moçambicanos ─────────────────────────────────────────

PREFIXOS_MOVITEL = ('86', '87')
PREFIXOS_VODACOM = ('84', '85')
PREFIXOS_TMCEL = ('82', '83')
TODOS_PREFIXOS = PREFIXOS_MOVITEL + PREFIXOS_VODACOM + PREFIXOS_TMCEL


def normalizar_numero(numero: str) -> Optional[str]:
    """
    Normaliza um número moçambicano para o formato E.164 (+258XXXXXXXXX).

    Aceita:
      84 123 4567   → +258841234567
      0841234567    → +258841234567
      +258841234567 → +258841234567
      258841234567  → +258841234567

    Devolve None se o número for inválido.
    """
    if not numero:
        return None

    # Remover espaços, hífens, parênteses
    limpo = re.sub(r'[\s\-\(\)]', '', numero)

    # Já está em formato E.164
    if limpo.startswith('+258') and len(limpo) == 13:
        prefixo = limpo[4:6]
        if prefixo in TODOS_PREFIXOS:
            return limpo

    # Formato 258XXXXXXXXX
    if limpo.startswith('258') and len(limpo) == 12:
        prefixo = limpo[3:5]
        if prefixo in TODOS_PREFIXOS:
            return f'+{limpo}'

    # Formato 0XXXXXXXXX
    if limpo.startswith('0') and len(limpo) == 10:
        prefixo = limpo[1:3]
        if prefixo in TODOS_PREFIXOS:
            return f'+258{limpo[1:]}'

    # Formato XXXXXXXXX (9 dígitos sem prefixo de país)
    if len(limpo) == 9 and limpo[:2] in TODOS_PREFIXOS:
        return f'+258{limpo}'

    logger.warning('Número inválido ou não reconhecido: %s', numero)
    return None


def identificar_operador(numero: str) -> str:
    """
    Identifica o operador de um número normalizado (+258XXXXXXXXX).
    Devolve 'Movitel', 'Vodacom', 'Tmcel' ou 'Desconhecido'.
    """
    if not numero or len(numero) < 6:
        return 'Desconhecido'

    prefixo = numero[4:6]  # ex: '84' de '+258841234567'

    if prefixo in PREFIXOS_MOVITEL:
        return 'Movitel'
    if prefixo in PREFIXOS_VODACOM:
        return 'Vodacom'
    if prefixo in PREFIXOS_TMCEL:
        return 'Tmcel'
    return 'Desconhecido'


# ── Cliente Africa's Talking ──────────────────────────────────────────────────

def _get_client():
    """
    Inicializa e devolve o cliente Africa's Talking.
    Levanta ImproperlyConfigured se as credenciais não estiverem definidas.
    """
    try:
        import africastalking
    except ImportError:
        raise ImportError(
            "Pacote 'africastalking' não instalado. "
            "Adiciona 'africastalking' ao requirements.txt e reinstala."
        )

    username = getattr(settings, 'AT_USERNAME', None)
    api_key = getattr(settings, 'AT_API_KEY', None)

    if not username or not api_key:
        raise ValueError(
            "AT_USERNAME e AT_API_KEY devem estar definidos no .env. "
            "Em sandbox usa AT_USERNAME=sandbox."
        )

    africastalking.initialize(username, api_key)
    return africastalking.SMS


def enviar_sms(destinatario: str, mensagem: str, sender_id: str = None) -> dict:
    """
    Envia um SMS via Africa's Talking.

    Parâmetros:
        destinatario — número no formato moçambicano (qualquer formato aceite)
        mensagem     — texto do SMS (máx. 160 caracteres por SMS simples)
        sender_id    — ID do remetente (opcional, ex: 'ESCOLA')

    Devolve:
        {
            'sucesso': True | False,
            'numero': '+258841234567',
            'operador': 'Movitel' | 'Vodacom' | 'Tmcel',
            'messageId': 'ATXid_...',
            'cost': 'MZN 1.50',
            'status': 'Success',
            'erro': None | 'mensagem de erro',
        }
    """
    numero_normalizado = normalizar_numero(destinatario)
    if not numero_normalizado:
        return {
            'sucesso': False,
            'numero': destinatario,
            'operador': 'Desconhecido',
            'erro': f'Número inválido: {destinatario}',
        }

    operador = identificar_operador(numero_normalizado)

    try:
        sms = _get_client()
        kwargs = {
            'message': mensagem,
            'recipients': [numero_normalizado],
        }
        if sender_id:
            kwargs['senderId'] = sender_id

        resposta = sms.send(**kwargs)
        recipients = resposta.get('SMSMessageData', {}).get('Recipients', [])

        if recipients:
            r = recipients[0]
            sucesso = r.get('status', '').lower() == 'success'
            return {
                'sucesso': sucesso,
                'numero': numero_normalizado,
                'operador': operador,
                'messageId': r.get('messageId', ''),
                'cost': r.get('cost', ''),
                'status': r.get('status', ''),
                'erro': None if sucesso else r.get('status'),
            }

        return {
            'sucesso': False,
            'numero': numero_normalizado,
            'operador': operador,
            'erro': 'Resposta vazia do Africa\'s Talking',
        }

    except Exception as exc:
        logger.error(
            'Erro ao enviar SMS para %s (%s): %s',
            numero_normalizado, operador, exc
        )
        return {
            'sucesso': False,
            'numero': numero_normalizado,
            'operador': operador,
            'erro': str(exc),
        }


def enviar_sms_bulk(destinatarios: List[str], mensagem: str, sender_id: str = None) -> List[Dict]:
    """
    Envia o mesmo SMS para múltiplos destinatários.

    Parâmetros:
        destinatarios — lista de números moçambicanos
        mensagem      — texto do SMS

    Devolve lista de resultados, um por destinatário.
    """
    if not destinatarios:
        return []

    numeros_validos = []
    numeros_invalidos = []

    for n in destinatarios:
        normalizado = normalizar_numero(n)
        if normalizado:
            numeros_validos.append(normalizado)
        else:
            numeros_invalidos.append(n)
            logger.warning('Número inválido ignorado: %s', n)

    resultados = []

    for n in numeros_invalidos:
        resultados.append({
            'sucesso': False,
            'numero': n,
            'operador': 'Desconhecido',
            'erro': f'Número inválido: {n}',
        })

    if not numeros_validos:
        return resultados

    try:
        sms = _get_client()
        kwargs = {
            'message': mensagem,
            'recipients': numeros_validos,
        }
        if sender_id:
            kwargs['senderId'] = sender_id

        resposta = sms.send(**kwargs)
        recipients = resposta.get('SMSMessageData', {}).get('Recipients', [])

        mapa = {r.get('number'): r for r in recipients}

        for numero in numeros_validos:
            r = mapa.get(numero, {})
            sucesso = r.get('status', '').lower() == 'success'
            resultados.append({
                'sucesso': sucesso,
                'numero': numero,
                'operador': identificar_operador(numero),
                'messageId': r.get('messageId', ''),
                'cost': r.get('cost', ''),
                'status': r.get('status', ''),
                'erro': None if sucesso else r.get('status', 'Sem resposta'),
            })

    except Exception as exc:
        logger.error('Erro ao enviar SMS bulk: %s', exc)
        for numero in numeros_validos:
            resultados.append({
                'sucesso': False,
                'numero': numero,
                'operador': identificar_operador(numero),
                'erro': str(exc),
            })

    return resultados
