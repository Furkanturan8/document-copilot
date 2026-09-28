from ingest.sec_tables import extract_sec_tables


def html(*blocks: str) -> str:
    return "<html><body>" + "".join(blocks) + "</body></html>"


# Shaped like Apple's 10-K "net sales by category" table: colspan cells, "$" and "%" in
# their own cells, empty spacer cells, and a group of year/Change headers.
NET_SALES = """
<div><span>The following table shows net sales by category (dollars in millions):</span></div>
<table>
  <tr><td colspan="3"/><td colspan="3"><span>2024</span></td><td/><td colspan="3"><span>Change</span></td>
      <td/><td colspan="3"><span>2023</span></td></tr>
  <tr><td colspan="3"><span>iPhone</span></td><td><span>$</span></td><td><span>201,183&#160;</span></td><td/><td/>
      <td colspan="2"><span>&#8212;&#160;</span></td><td><span>%</span></td><td/><td><span>$</span></td>
      <td><span>200,583&#160;</span></td><td/></tr>
  <tr><td colspan="3"><span>Mac</span></td><td colspan="2"><span>29,984</span></td><td/><td/>
      <td colspan="2"><span>(6)</span></td><td><span>%</span></td><td/><td colspan="2"><span>29,357</span></td><td/></tr>
</table>
"""


def test_rebuilds_financial_table_without_grid_noise():
    [table] = extract_sec_tables(html(NET_SALES))

    assert table.table_data["columns"] == ["", "2024", "Change", "2023"]
    assert table.table_data["rows"] == [
        {"label": "iPhone", "values": ["$201,183", "—%", "$200,583"]},
        {"label": "Mac", "values": ["29,984", "(6)%", "29,357"]},
    ]
    assert table.markdown.splitlines()[2] == "| iPhone | $201,183 | —% | $200,583 |"
    assert table.title == "The following table shows net sales by category (dollars in millions):"
    assert table.units == "in millions"


def test_hidden_xbrl_header_is_ignored():
    hidden = '<div style="display:none"><table><tr><td>Revenue</td><td>$1,000</td></tr></table></div>'
    assert len(extract_sec_tables(html(hidden, NET_SALES))) == 1


def test_year_only_row_with_units_label_is_a_header():
    # Microsoft puts the units in the label cell of the year row.
    table = """
    <table>
      <tr><td>(In millions, except percentages)</td><td>2024</td><td>2023</td><td>Percentage Change</td></tr>
      <tr><td>Revenue</td><td>$245,122</td><td>$211,915</td><td>16%</td></tr>
    </table>"""
    [result] = extract_sec_tables(html(table))

    assert result.table_data["columns"] == ["(In millions, except percentages)", "2024", "2023", "Percentage Change"]
    assert result.table_data["rows"] == [{"label": "Revenue", "values": ["$245,122", "$211,915", "16%"]}]
    assert result.units == "In millions, except percentages"


def test_label_only_row_before_data_is_a_section_not_a_header():
    table = """
    <table>
      <tr><td/><td>2024</td><td>2023</td></tr>
      <tr><td>Designated as hedges:</td><td/><td/></tr>
      <tr><td>Foreign exchange contracts</td><td>$64,069</td><td>$74,730</td></tr>
    </table>"""
    [result] = extract_sec_tables(html(table))

    assert result.table_data["columns"] == ["", "2024", "2023"]
    assert result.table_data["rows"][0] == {"label": "Designated as hedges:", "values": [None, None]}


def test_rowspan_header_does_not_shift_the_next_header_row():
    # Apple's debt table: "Maturities" spans two header rows.
    table = """
    <table>
      <tr><td/><td rowspan="2">Maturities</td><td colspan="2">2021</td></tr>
      <tr><td/><td>Amount</td><td>Rate</td></tr>
      <tr><td>Floating-rate notes</td><td>2022</td><td>$1,750</td><td>0.48%</td><td>–</td><td>0.63%</td></tr>
    </table>"""
    [result] = extract_sec_tables(html(table))

    assert result.table_data["columns"] == ["", "Maturities", "2021 Amount", "2021 Rate"]
    assert result.table_data["rows"][0]["values"] == ["2022", "$1,750", "0.48% – 0.63%"]


def test_em_dash_nil_placeholder_stays_its_own_value():
    table = """
    <table>
      <tr><td/><td>2024</td><td>2023</td><td>2022</td></tr>
      <tr><td>Impairments</td><td>$1,200</td><td>—</td><td>$900</td></tr>
    </table>"""
    [result] = extract_sec_tables(html(table))
    assert result.table_data["rows"][0]["values"] == ["$1,200", "—", "$900"]


def test_text_change_column_keeps_its_own_column():
    table = """
    <table>
      <tr><td/><td>2021</td><td>2020</td><td>Change</td></tr>
      <tr><td>Revenue</td><td>$16,675</td><td>$10,918</td><td>Up 53%</td></tr>
    </table>"""
    [result] = extract_sec_tables(html(table))
    assert result.table_data["rows"][0]["values"] == ["$16,675", "$10,918", "Up 53%"]


def test_layout_tables_are_skipped():
    prose = "<table><tr><td>•</td><td>" + "Commercial cloud revenue increased 34% to $69.1 billion. " * 5 + "</td></tr></table>"
    exhibits = """
    <table>
      <tr><td>Exhibit Number</td><td>Description</td></tr>
      <tr><td>4.12</td><td>1.100% Notes due 2019</td></tr>
    </table>"""
    contents = """
    <table>
      <tr><td>Item 1A.</td><td>Risk Factors</td><td>5</td></tr>
      <tr><td>Item 7.</td><td>Management's Discussion</td><td>21</td></tr>
    </table>"""
    assert extract_sec_tables(html(prose, exhibits, contents)) == []


def test_tables_are_indexed_in_document_order():
    tables = extract_sec_tables(html(NET_SALES, NET_SALES.replace("iPhone", "iPad")))
    assert [table.table_index for table in tables] == [0, 1]
    assert "iPad" in tables[1].markdown
