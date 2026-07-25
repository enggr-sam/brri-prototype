/** USD → BDT for display (override via VITE_USD_TO_BDT in frontend .env). */
const USD_TO_BDT = Number(import.meta.env.VITE_USD_TO_BDT) || 120;

function bnNumber(value) {
  return Number(value).toLocaleString("bn-BD");
}

function usdInParens(usd) {
  return `($${Number(usd).toFixed(4)} USD)`;
}

/** e.g. "২৪ পয়সা ($0.0020 USD)" or "১ টাকা ৫০ পয়সা ($0.0015 USD)" */
export function formatCostBdt(usd) {
  const amount = Math.max(0, Number(usd) || 0);
  const totalPaisa = Math.round(amount * USD_TO_BDT * 100);
  const taka = Math.floor(totalPaisa / 100);
  const poisa = totalPaisa % 100;

  let bdtPart;
  if (taka > 0 && poisa > 0) {
    bdtPart = `${bnNumber(taka)} টাকা ${bnNumber(poisa)} পয়সা`;
  } else if (taka > 0) {
    bdtPart = `${bnNumber(taka)} টাকা`;
  } else if (poisa > 0) {
    bdtPart = `${bnNumber(poisa)} পয়সা`;
  } else {
    bdtPart = "০ টাকা";
  }

  return `${bdtPart} ${usdInParens(amount)}`;
}

/** Session header — cost incurred in this conversation so far. */
export function formatSessionCostLabel(usd) {
  return `এই কথোপকথনে এ পর্যন্ত যে খরচ হয়েছে: ${formatCostBdt(usd)}`;
}

/** Per-reply cost line under an assistant bubble. */
export function formatReplyCostLabel(usd) {
  return `এই উত্তরের খরচ: ${formatCostBdt(usd)}`;
}
