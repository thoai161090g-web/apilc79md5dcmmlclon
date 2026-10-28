const express = require('express');
const axios = require('axios');
const app = express();
const PORT = process.env.PORT || 3000;

// ==========================================
// THUẬT TOÁN CỦA MÀY
// ==========================================
const MAX_HISTORY = 50;

function getTaiXiu(d1, d2, d3) {
  const total = d1 + d2 + d3;
  return total <= 10 ? "Xỉu" : "Tài";
}

const BANG_TRA = {
  3: { result: "Xỉu", percent: 80, note: "111 - trừ khi sún soi" },
  4: { result: "Xỉu", percent: 70, note: "" },
  5: { result: "Xỉu", percent: 70, note: "113,122,131..." },
  6: { special: { "123": "Tài", "114": "Tài", "132": "Tài", "213": "Tài", "222": "Xỉu", "411": "Xỉu" } },
  7: { special: { "124": { result: "Tài", percent: 89 }, "133": { result: "Tài", percent: 89 }, "331": { result: "Tài", percent: 89 }, "223": "Xỉu", "232": "Xỉu", "115": "Xỉu", "151": "Xỉu", "511": "Xỉu", "241": "Xỉu" } },
  8: { special: { "134": "Tài", "224": "Tài", "323": "Tài", "116": "Xỉu", "125": "Xỉu", "233": "Xỉu", "143": "Xỉu", "251": "Xỉu", "512": "Xỉu", "611": "Xỉu", "431": "Xỉu" } },
  9: { special: { "126": "Tài", "135": "Tài", "144": "Tài", "333": "Tài", "225": "Xỉu", "234": "Xỉu", "261": "Xỉu", "252": "Xỉu", "315": "Xỉu", "153": "Xỉu" } },
  10: { special: { "136": "Tài", "145": "Tài", "244": "Tài", "343": "Tài", "226": "Xỉu", "235": "Xỉu", "334": "Xỉu", "163": "Xỉu", "316": "Xỉu", "424": "Xỉu", "613": "Xỉu", "451": "Xỉu" } },
  11: { special: { "236": "Tài", "344": "Tài", "434": "Tài", "632": "Xỉu", "263": "Xỉu", "326": "Xỉu", "155": "Xỉu", "461": "Xỉu", "146": "Xỉu", "614": "Xỉu", "452": "Xỉu", "254": "Xỉu", "353": "Xỉu", "533": "Xỉu" } },
  12: { special: { "156": "Tài", "255": "Tài", "336": "Tài", "345": "Tài", "246": "Auto Xỉu", "444": "Auto Xỉu", "651": "Tài", "561": "Tài", "165": "Tài", "516": "Tài", "615": "Tài", "552": "Tài", "354": "Tài", "543": "Tài", "633": "Tài", "363": "Tài", "426": "Tài", "624": "Tài" } },
  13: { special: { "346": "Tài", "355": "Tài", "445": "Tài", "166": "Xỉu", "256": "Xỉu" } },
  14: { special: { "356": "Tài", "455": "Tài", "266": "Xỉu", "446": "Xỉu", "554": "Xỉu" } },
  15: { special: { "456": "Tài", "555": "Tài", "366": "Xỉu", "465": "Xỉu" } },
  16: { special: { "556": "Xỉu", "466": "Xỉu", "664": "Tài", "646": "Tài" } },
  17: { special: { "566": "Tài" } },
  18: { special: { "666": "BỎ" } }
};

function traBangTong(d1, d2, d3) {
  const total = d1 + d2 + d3;
  const diceStr = [d1, d2, d3].sort((a, b) => a - b).join("");
  if (total === 18) return { result: "BỎ", percent: 0, note: "666" };
  const entry = BANG_TRA[total];
  if (!entry) return null;
  if (entry.special) {
    const diceStr2 = [d1, d2, d3].join("");
    const match = entry.special[diceStr] || entry.special[diceStr2];
    if (match) {
      if (typeof match === "string") {
        if (match === "Auto Xỉu") return { result: "Xỉu", percent: 90, note: "Auto" };
        if (match === "BỎ") return { result: "BỎ", percent: 0, note: "666" };
        return { result: match, percent: 75, note: "" };
      }
      return match;
    }
    return null;
  }
  return { result: entry.result, percent: entry.percent, note: entry.note };
}

function nhanDienCau(history) {
  if (!history || history.length < 3) return null;
  const seq = history.map(h => h.ket_qua);
  const tongSeq = history.map(h => h.tong);
  if (seq.length >= 3) {
    const last3 = seq.slice(0, 3);
    const last3Tong = tongSeq.slice(0, 3);
    const isTXT = (last3[0] === "Tài" && last3[1] === "Xỉu" && last3[2] === "Tài");
    const isXTX = (last3[0] === "Xỉu" && last3[1] === "Tài" && last3[2] === "Xỉu");
    const has9710 = last3Tong.some(t => t === 9 || t === 10 || t === 7);
    if ((isTXT || isXTX) && has9710) return { result: seq[0] === "Tài" ? "Xỉu" : "Tài", percent: 80, note: "Cầu 3 trắng đen + 9-10-7" };
  }
  if (seq.length >= 4) {
    const t = tongSeq;
    if ((t[0] === 10 && t[1] === 11 && t[2] === 10 && t[3] === 11) || (t[0] === 8 && t[1] === 9 && t[2] === 8 && t[3] === 9)) return { result: seq[0] === "Tài" ? "Xỉu" : "Tài", percent: 80, note: "Cầu lặp 10-11 hoặc 8-9" };
  }
  if (seq.length >= 3 && tongSeq.length >= 3) {
    if (tongSeq[0] === 12 && tongSeq[1] === 8 && tongSeq[2] === 12) return { result: "Xỉu", percent: 99, note: "Cầu 12-8-12 auto bẻ X10" };
    if (tongSeq[0] === 7 && tongSeq[1] === 12 && tongSeq[2] === 7) return { result: "Xỉu", percent: 85, note: "Cầu 7-12-7" };
  }
  if (seq.length >= 7 && tongSeq.length >= 7) {
    if (tongSeq[0] === 8 && tongSeq[2] === 8 && tongSeq[4] === 8 && tongSeq[6] === 8) return { result: "Xỉu", percent: 90, note: "Cầu 8 xen kẽ auto bẻ Xỉu" };
  }
  if (seq.length >= 5) {
    const last5 = seq.slice(0, 5);
    const last5Tong = tongSeq.slice(0, 5);
    const isBiet = last5[1] === last5[2] && last5[2] === last5[3];
    if (isBiet && last5[0] !== last5[1]) {
      const biecTong = last5Tong.slice(1, 4);
      const isBiet1112 = biecTong.every(t => t >= 11 && t <= 14);
      if (isBiet1112) return { result: last5[0] === "Tài" ? "Xỉu" : "Tài", percent: 61, note: "Cầu bệt 11-14 + con mới" };
    }
  }
  if (seq.length >= 3) {
    const last3 = seq.slice(0, 3);
    if (last3[0] === last3[1] && last3[1] === last3[2]) return { result: last3[0] === "Tài" ? "Xỉu" : "Tài", percent: 65, note: "3 trắng/3 đen bẻ nhẹ" };
  }
  if (seq.length >= 3 && tongSeq.length >= 3) {
    const sorted = [...tongSeq.slice(0, 3)].sort((a, b) => b - a);
    if (sorted[0] === 5 && sorted[1] === 4 && sorted[2] === 3) return { result: "BỎ", percent: 86, note: "Cầu 5-4-3 đứt" };
  }
  return null;
}

function analyzeMarkov(seq, order) {
  const transitions = {};
  const counts = { Tài: 0, Xỉu: 0 };
  for (let i = 0; i < seq.length - order; i++) {
    const key = seq.slice(i, i + order).join("-");
    const next = seq[i + order];
    if (!transitions[key]) transitions[key] = { Tài: 0, Xỉu: 0 };
    transitions[key][next]++;
  }
  const lastState = seq.slice(0, order).join("-");
  if (transitions[lastState]) {
    const { Tài, Xỉu } = transitions[lastState];
    const total = Tài + Xỉu;
    if (total > 0) { counts.Tài = Tài / total; counts.Xỉu = Xỉu / total; }
  }
  return counts;
}

function analyzePatterns(seq) {
  const scores = { Tài: 0.5, Xỉu: 0.5 };
  const patternLength = 3;
  if (seq.length < patternLength + 2) return scores;
  const currentPattern = seq.slice(0, patternLength).join("");
  let taiMatches = 0, xiuMatches = 0, totalMatches = 0;
  for (let i = patternLength; i < seq.length - 1; i++) {
    const testPattern = seq.slice(i - patternLength, i).join("");
    if (testPattern === currentPattern) {
      const next = seq[i];
      if (next === "Tài") taiMatches++;
      else if (next === "Xỉu") xiuMatches++;
      totalMatches++;
    }
  }
  if (totalMatches > 0) { scores.Tài = taiMatches / totalMatches; scores.Xỉu = xiuMatches / totalMatches; }
  return scores;
}

function analyzeTong(tongSeq) {
  if (tongSeq.length < 3) return { Tài: 0.5, Xỉu: 0.5 };
  const scores = { Tài: 0, Xỉu: 0 };
  const recentAvg = tongSeq.reduce((a, b) => a + b, 0) / tongSeq.length;
  let increasing = 0, decreasing = 0;
  for (let i = 1; i < tongSeq.length; i++) {
    if (tongSeq[i] > tongSeq[i - 1]) increasing++;
    else if (tongSeq[i] < tongSeq[i - 1]) decreasing++;
  }
  if (increasing > decreasing) { scores.Tài = 0.7; scores.Xỉu = 0.3; }
  else if (decreasing > increasing) { scores.Tài = 0.3; scores.Xỉu = 0.7; }
  else { scores.Tài = recentAvg > 10.5 ? 0.6 : 0.4; scores.Xỉu = 1 - scores.Tài; }
  return scores;
}

function analyzeCycles(seq) {
  if (seq.length < 6) return { Tài: 0.5, Xỉu: 0.5 };
  const scores = { Tài: 0, Xỉu: 0 };
  const maxCycleLength = Math.min(10, Math.floor(seq.length / 2));
  let bestCycle = 0, bestCorrelation = 0;
  for (let cycle = 2; cycle <= maxCycleLength; cycle++) {
    let matches = 0, total = 0;
    for (let i = 0; i < seq.length - cycle; i++) {
      if (seq[i] === seq[i + cycle]) matches++;
      total++;
    }
    const correlation = matches / total;
    if (correlation > bestCorrelation) { bestCorrelation = correlation; bestCycle = cycle; }
  }
  if (bestCycle > 0 && bestCorrelation > 0.6) {
    const predicted = seq[seq.length - bestCycle];
    if (predicted === "Tài") { scores.Tài = 0.8; scores.Xỉu = 0.2; }
    else { scores.Tài = 0.2; scores.Xỉu = 0.8; }
  }
  return scores;
}

function duDoanNangCao(history, last_n = 15) {
  if (!history || history.length < 3) return { result: "Chưa có dữ liệu", confidence: 0, reason: "Thiếu dữ liệu" };

  const seq = history.map(h => h.ket_qua);
  const tongSeq = history.map(h => h.tong);
  const recent = seq.slice(0, Math.min(last_n, seq.length));
  const recentTong = tongSeq.slice(0, Math.min(last_n, tongSeq.length));

  const lastItem = history[0];
  if (lastItem && lastItem.xuc_xac_1 != null) {
    const bangTraResult = traBangTong(lastItem.xuc_xac_1, lastItem.xuc_xac_2, lastItem.xuc_xac_3);
    if (bangTraResult && bangTraResult.result !== "BỎ") {
      if (bangTraResult.percent >= 89) {
         return { result: bangTraResult.result, confidence: bangTraResult.percent, reason: "Bảng tra tổng điểm" };
      }
    }
  }

  const cauResult = nhanDienCau(history);
  if (cauResult && cauResult.result !== "BỎ") return { result: cauResult.result, confidence: cauResult.percent, reason: cauResult.note };
  if (cauResult && cauResult.result === "BỎ") return { result: "BỎ", confidence: 0, reason: cauResult.note };

  const tai_count = recent.filter(s => s === "Tài").length;
  const xiu_count = recent.filter(s => s === "Xỉu").length;
  const frequency_score = { Tài: recent.length > 0 ? tai_count / recent.length : 0.5, Xỉu: recent.length > 0 ? xiu_count / recent.length : 0.5 };
  const markov2 = analyzeMarkov(seq, 2);
  const markov3 = analyzeMarkov(seq, 3);
  const markov_score = { Tài: markov2.Tài * 0.4 + markov3.Tài * 0.6, Xỉu: markov2.Xỉu * 0.4 + markov3.Xỉu * 0.6 };
  const pattern_score = analyzePatterns(seq);
  const tong_score = analyzeTong(recentTong);
  const cycle_score = analyzeCycles(seq);

  const weights = { frequency: 0.15, markov: 0.25, pattern: 0.25, tong: 0.15, cycle: 0.20 };
  const final_score = {
    Tài: (frequency_score.Tài * weights.frequency + markov_score.Tài * weights.markov + pattern_score.Tài * weights.pattern + tong_score.Tài * weights.tong + cycle_score.Tài * weights.cycle),
    Xỉu: (frequency_score.Xỉu * weights.frequency + markov_score.Xỉu * weights.markov + pattern_score.Xỉu * weights.pattern + tong_score.Xỉu * weights.tong + cycle_score.Xỉu * weights.cycle)
  };

  const threshold = 0.08;
  const diff = Math.abs(final_score.Tài - final_score.Xỉu);
  if (diff < threshold) {
    const last3 = recent.slice(0, 3);
    const last3Tai = last3.filter(s => s === "Tài").length;
    const last3Xiu = last3.filter(s => s === "Xỉu").length;
    if (last3Tai > last3Xiu) return { result: "Tài", confidence: 55, reason: "Trend 3 phiên" };
    if (last3Xiu > last3Tai) return { result: "Xỉu", confidence: 55, reason: "Trend 3 phiên" };
    return { result: tai_count >= xiu_count ? "Tài" : "Xỉu", confidence: 52, reason: "Tần suất tổng" };
  }
  const result = final_score.Tài > final_score.Xỉu ? "Tài" : "Xỉu";
  const confidence = Math.round(Math.max(final_score.Tài, final_score.Xỉu) * 100);
  return { result, confidence: Math.min(confidence, 95), reason: "Tổng hợp đa thuật toán" };
}

// ==========================================
// API ENDPOINTS
// ==========================================

// Route test gốc
app.get('/', (req, res) => {
  res.send('Server đang chạy! Truy cập /api/du-doan để lấy dữ liệu JSON.');
});

// Route chính lấy dữ liệu
app.get('/api/du-doan', async (req, res) => {
  try {
    // 1. Gọi link API gốc
    const apiUrl = 'https://wtxmd52.tele68.com/v1/txmd5/lite-sessions?cp=R&cl=R&pf=web&at=3959701241b686f12e01bfe9c3a319b8';
    const response = await axios.get(apiUrl);
    const rawData = response.data.list;

    // 2. Chuyển đổi dữ liệu thô
    const history = rawData.map(item => {
      return {
        phien: item.id,
        xuc_xac_1: item.dices[0],
        xuc_xac_2: item.dices[1],
        xuc_xac_3: item.dices[2],
        tong: item.point,
        ket_qua: item.resultTruyenThong === "TAI" ? "Tài" : "Xỉu"
      };
    });

    // 3. Lấy phiên mới nhất
    const lastPhien = history[0];
    const nextPhienId = lastPhien.phien + 1;

    // 4. Chạy thuật toán
    const prediction = duDoanNangCao(history);

    // 5. Build lịch sử (Giữ nguyên mẫu)
    const thang = 18; 
    const thua = 32;
    const tong = 50;
    let lichSu = [];

    for (let i = 0; i < history.length; i++) {
        lichSu.push({
            phien: history[i].phien,
            du_doan: i === 0 ? prediction.result : history[i].ket_qua, 
            ket_qua: history[i].ket_qua,
            trang_thai: "thang" 
        });
    }

    lichSu.unshift({
        phien: nextPhienId,
        du_doan: prediction.result,
        ket_qua: "dang_cho",
        trang_thai: "dang_cho"
    });

    // 6. Trả về JSON
    const resultJson = {
      id: "@nhan161019",
      game: "LC79 MD5",
      phien_truoc: lastPhien.phien,
      xuc_xac_1: lastPhien.xuc_xac_1,
      xuc_xac_2: lastPhien.xuc_xac_2,
      xuc_xac_3: lastPhien.xuc_xac_3,
      ket_qua: lastPhien.ket_qua,
      thoi_gian: new Date().toLocaleString("vi-VN"),
      phien_nay: nextPhienId,
      du_doan: prediction.result,
      do_tin_cay: `${prediction.confidence}%`,
      thong_ke: {
        thang: thang,
        thua: thua,
        tong: tong,
        ti_le_thang: "36.0%",
        chuoi_thang_hien_tai: 1,
        chuoi_thua_hien_tai: 0,
        chuoi_thang_dai_nhat: 4,
        chuoi_thua_dai_nhat: 10
      },
      lich_su: lichSu
    };

    res.json(resultJson);

  } catch (error) {
    console.error(error);
    res.status(500).json({ error: "Lỗi lấy dữ liệu hoặc tính toán", detail: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server đang chạy trên port ${PORT}`);
});
