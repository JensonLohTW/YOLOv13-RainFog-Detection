# 第一階段： Node.js 打包 Vite 靜態前端程式碼
FROM node:18-alpine AS builder

WORKDIR /app

# 僅複製宣告文檔優先執行依賴抓取以最大化利用快取
COPY package.json package-lock.json* ./
RUN npm ci

# 搬入所有程式碼並編譯 TypeScript (TypeScript 需先修復 node resolution 錯誤，否則 CI 將中斷)
COPY . .
RUN npm run build

# 第二階段： 採用 Nginx 作為高速靜態代理
FROM nginx:alpine

# 導入由 Builder 產生之最終編譯產出結果（位在 /dist）
COPY --from=builder /app/dist /usr/share/nginx/html

# 手動將客製化 Nginx 設置推入，宣告 SPA 的重新導向、及將後端請求轉發
RUN echo 'server {\n\
    listen 80;\n\
    \n\
    # 靜態首頁服務與 React Route 的 404 對接\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        index index.html index.htm;\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
    \n\
    # 後端 Django API 的網域反向代理\n\
    location /api/ {\n\
        proxy_pass http://backend:8000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    # 後端 Django 用戶上傳與輸出圖的媒介目錄代理\n\
    location /media/ {\n\
        proxy_pass http://backend:8000;\n\
        proxy_set_header Host $host;\n\
    }\n\
    \n\
    # 推理結果圖片代理\n\
    location /media-results/ {\n\
        proxy_pass http://backend:8000;\n\
        proxy_set_header Host $host;\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

# 暴露出服務對內 80 端口 (外部在 Compose 重導至 5173 或 80)
EXPOSE 80

# 抑制守護行程式以使容器不退出
CMD ["nginx", "-g", "daemon off;"]
