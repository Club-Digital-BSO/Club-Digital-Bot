# Club-Digital Bot

Dieses Projekt ist ein Bot, der als Helfer für den Club-Digital Server gedacht ist.
Dieses Projekt wird von Schülern entwickelt.

## Voraussetzungen:

 - Python 3.10
 - poetry
 - Code Editor (empfohlen: Pycharm community)
 - Alembic

## Bibliotheken

 - pycord
 - dotenvy
 - SQLAlchemy
 - loguru

## Installation

 1. Projekt clonen:
    Bevor du am Projekt arbeiten kannst, musst du zuerst das Projekt runterladen.
    Dafür kannst du das Programm `git` benutzen, dann nennt man diesen Vorgang "clonen".
    Wie du git installierst und wie du ein Projekt clonst und wie das vielleicht mit einer von vielen GUIs funktioniert kannst du auf unserem Server nachlesen.
    Ich werde hier nur die Befehle zeigen, die du benutzt, wenn du ein Debian basiertes Linux und das Terminal benutzt.  
    Zusätzlich zu den Befehlen werde ich ein Script zur Verfügung stellen, das die ganzen Befehle zusammenfasst.
    ```bash
    git clone https://github.com/Club-Digital-BSO/Club-Digital-Bot.git
    ```
 2. Poetry installieren
    Poetry ist ein Tool, das das Bauen von Dingen in python deutlich verbessert.
    Die Dokumentation von poetry findest du unter: [python-poetry.org](https://python-poetry.org/docs/)  
    Um es zu installieren kannst du unter Linux den folgenden Befehl verwenden. 
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```
 3. Projekt installieren
    Bevor du anfangen kannst, musst du die Bibliotheken für das Projekt installieren.
    Dabei werden die Bibliotheken, die der Bot braucht heruntergeladen und in einer eigenen Umgebung gelagert.
    Außerdem baut poetry ein Paket zusammen, das man mit dem normalen Paketmanager für python installieren kann.
    Die genaue Anleitung findest du auch hier auf Discord.  
    Der Befehl dafür lautet:
    ```bash
    poetry install
    ```
 4. In IDE importieren
    Wie du das Projekt in VS-Code oder PyCharm integrierst, findest du auf Discord.
 5. Projekt starten
     Du kannst das Projekt starten, indem du Poetry einen Befehl in der Umgebung des Projekts ausführen lässt.
     ```bash
     poetry run python ClubDigital/main.py
     ```