# XMLRPC-Shogi (網路對戰將棋)

[![Python Version](https://shields.io)](https://python.org)
[![Framework](https://shields.io)](https://pygame.org)
[![Protocol](https://shields.io)](https://python.org)

一個基於 Python 開發的網路對戰將棋（Shogi）專案。本專案核心採用 **前後端解耦架構**，前端利用 Pygame 打造流暢的圖形化使用者介面（GUI），後端則透過 XML-RPC 遠端程序呼叫協定（Remote Procedure Call）實現輕量化的遊戲邏輯驗證與網絡通訊狀態同步。

---

## 專案亮點與核心架構

本專案不僅是一個遊戲，更是實作**分散式系統通訊**與**前後端分離思維**的技術作品：

- **前後端解耦設計 (Decoupled Architecture)**：
  - **客戶端 (Frontend/Client)**：僅負責補捉玩家點擊事件、本機 UI 渲染（Render）與顯示棋盤局勢，保持客戶端極輕量化。
  - **服務端 (Backend/Server)**：封裝完整的將棋遊戲規則、步法合法性驗證（Rule Validation）及局勢狀態（Game State）管理。
- **遠端程序呼叫 (XML-RPC Protocol)**：
  - 放棄傳統複雜的低階 Socket 連線，改採用高階的 XML-RPC 協定。
  - 將玩家的「下子、移動、吃子」等動作抽象化為結構化的遠端方法呼叫（RPC Methods），確保資料傳輸的嚴謹度與可擴充性。
- **雙向驗證機制 (Security & Integrity)**：
  - 所有棋步移動皆由後端伺服器做最終邏輯判定，防範客戶端竄改數據（防作弊機制），確保遊戲公平性。

---

## 技術堆疊 (Tech Stack)

- **開發語言**：Python 3.x
- **前端 GUI**：Pygame (處理 9x9 棋盤渲染、動態選取、棋子繪製)
- **網路通訊**：`xmlrpc.client` & `xmlrpc.server` (標準庫)
- **版本控制**：Git / GitHub

---

## 檔案結構說明

```text
├── final_pygame/        # 專案核心程式碼目錄
│   ├── server.py       # XML-RPC 後端伺服器 (負責規則驗證與狀態維護)
│   ├── client.py       # Pygame 前端客戶端 (負責 UI 互動與 RPC 呼叫)
│   └── [其餘相關圖資/邏輯檔案]
└── README.md            # 專案技術文件
```

---

## 快速開始 (Quick Start)

### 1. 環境準備
請確保您的環境已安裝 Python 3.8+，並安裝 Pygame 依賴：
```bash
pip install pygame
```

### 2. 啟動後端伺服器
首先在伺服器端（或本機）啟動 RPC Server，監聽連線並初始化遊戲局勢：
```bash
python final_pygame/server.py
```

### 3. 啟動前端客戶端
啟動客戶端程式，連線至伺服器即可開始進行將棋對戰：
```bash
python final_pygame/client.py
```

---

## 未來擴充規劃 (Future Roadmap)

為了因應更高併發（High Concurrency）與即時通訊的需求，本專案預計進行以下架構升級：
1. **通訊協定升級**：規劃將 XML-RPC 升級為 **WebSocket** 或 **gRPC**，引入雙向持久連線（Bi-directional Streaming），優化高延遲網路下的遊戲體驗。
2. **Web 端移植**：利用後端已解耦的特性，未來計畫使用 **React / TypeScript** 重構前端客戶端，將遊戲移植至 Web 瀏覽器端。
3. **資料庫整合**：預計導入 SQLite / PostgreSQL 進行玩家數據持久化（Persistence），記錄勝率與歷史對局（棋譜）。
