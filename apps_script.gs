// Google Apps Script: Web App to log webhook events into a Sheet.
// 1) Set SHEET_NAME below to your sheet tab name.
// 2) Deploy as Web app (Anyone with link).
// 3) Put the deployed URL into GOOGLESHEET_WEBAPP env var.

const SHEET_NAME = "Logs";

function doPost(e) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    const body = e.postData ? e.postData.contents : "{}";
    const obj = JSON.parse(body);

    const ts = obj.ts || Math.floor(Date.now()/1000);
    const date = new Date(ts * 1000);
    const action = obj.action || "";
    const symbol = obj.symbol || "";
    const reason = obj.reason || "";
    const usd = obj.usd || "";
    const response = obj.response || "";

    sh.appendRow([ts, date, action, symbol, reason, usd, response]);
    return ContentService.createTextOutput(JSON.stringify({ok:true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false, error: String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
