import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
import pandas as pd
import regex as re
import csv


scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def login():
    # Carregar credenciais do Google Sheets a partir de st.secrets
    credentials_info = st.secrets["google_sheets_credentials"]
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    scoped_credentials = credentials.with_scopes(scopes)
    gc = gspread.authorize(scoped_credentials)
    return gc


def escritor(lista,sheet,page):
    gc = login()
    planilha = gc.open(sheet)
    aba = planilha.worksheet(page)
    aba.append_row(lista, value_input_option='USER_ENTERED')


def escritor_cell(row, col, value, sheet, page):
    gc = login()
    planilha = gc.open(sheet)
    aba = planilha.worksheet(page)
    aba.update_cell(row, col, value)


def escritor_coluna(inicio_linha, coluna, valores, planilha_nome, pagina):
    """
    Escreve uma lista de valores em uma coluna inteira a partir de uma linha específica
    Args:
        inicio_linha (int): Número da linha inicial (base 1)
        coluna (int): Número da coluna (base 1)
        valores (list): Lista de valores a serem escritos
        planilha_nome (str): Nome da planilha
        pagina (str): Nome da página/aba
    """
    gc = login()
    planilha = gc.open(planilha_nome)
    aba = planilha.worksheet(pagina)
    
    # Converter números para notação A1
    range_inicio = f"{gspread.utils.rowcol_to_a1(inicio_linha, coluna)}"
    range_fim = f"{gspread.utils.rowcol_to_a1(inicio_linha + len(valores) - 1, coluna)}"
    
    # Formatar valores como lista de listas [[v1], [v2], ...]
    dados = [[valor] for valor in valores]
    
    aba.update(f"{range_inicio}:{range_fim}", dados)



def get_page(i,sheet,page): # (1) é o nome
    gc = login()
    planilha = gc.open(sheet)
    aba = planilha.worksheet(page)
    #lista = aba.col_values(i)
    lista = aba.get_all_records()
    return lista



def get_cell_inf(c,l, sheet, page): # c coluna
    gc = login()
    planilha = gc.open(sheet)
    aba = planilha.worksheet(page)
    # Encontrar a última linha preenchida
    col_values = aba.col_values(c)
    row = l
    url = str(aba.cell(row, c).value)

    return url