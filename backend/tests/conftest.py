"""
Shared pytest fixtures for steuerpilot-ai backend tests.
"""
import asyncio
import textwrap
from pathlib import Path

import aiosqlite
import pytest
import pytest_asyncio

from app.database import init_db


# ─── Event-loop (module-scoped so fixtures can share it) ──────────────────────

@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ─── In-memory SQLite DB ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    """Fresh in-memory SQLite connection with schema initialised."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await init_db(conn)
    yield conn
    await conn.close()


# ─── Minimal gesetze-im-internet.de XML fixture ───────────────────────────────

MINIMAL_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <dokumente>
      <norm>
        <metadaten>
          <jurabk>EStG</jurabk>
          <enbez>§ 4</enbez>
          <titel format="XML">Betriebsausgaben</titel>
        </metadaten>
        <textdaten>
          <fussnoten>
            <Content><P>(+++ Fußnote die ignoriert werden soll +++)</P></Content>
          </fussnoten>
          <text format="XML">
            <Content>
              <P>(1) Betriebsausgaben sind die Aufwendungen, die durch den Betrieb veranlasst sind.</P>
              <P>(2) Nicht abzugsfähig sind Aufwendungen gemäß § 12 dieses Gesetzes.</P>
            </Content>
          </text>
        </textdaten>
      </norm>
      <norm>
        <metadaten>
          <jurabk>EStG</jurabk>
          <enbez>§ 9</enbez>
          <titel format="XML">Werbungskosten</titel>
        </metadaten>
        <textdaten>
          <text format="XML">
            <Content>
              <P>(1) Werbungskosten sind Aufwendungen zur Erwerbung, Sicherung und Erhaltung der Einnahmen.</P>
              <P>(2) Hierzu gehören auch Arbeitsmittel i.V.m. § 4 Abs. 5.</P>
            </Content>
          </text>
        </textdaten>
      </norm>
      <norm>
        <metadaten>
          <jurabk>EStG</jurabk>
          <enbez>Inhaltsübersicht</enbez>
        </metadaten>
        <textdaten>
          <text format="XML"><Content><P>Dies ist eine Inhaltsübersicht ohne §.</P></Content></text>
        </textdaten>
      </norm>
      <norm>
        <metadaten>
          <!-- no <enbez> at all — should be skipped -->
          <jurabk>EStG</jurabk>
        </metadaten>
        <textdaten>
          <text format="XML"><Content><P>Irrelevant norm.</P></Content></text>
        </textdaten>
      </norm>
    </dokumente>
""")


@pytest.fixture
def xml_file(tmp_path) -> Path:
    """Write MINIMAL_XML to a temp file and return its path."""
    p = tmp_path / "EStG.xml"
    p.write_text(MINIMAL_XML, encoding="utf-8")
    return p
