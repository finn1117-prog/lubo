import { Controller, Get, Header } from '@nestjs/common';

const ADMIN_HTML = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>录播达人授权管理</title><style>
body{font:14px system-ui;margin:0;background:#f4f6f8;color:#17212b}main{max-width:1100px;margin:auto;padding:28px}section{background:white;padding:20px;margin:16px 0;border-radius:10px;box-shadow:0 2px 8px #0001}input,button{padding:9px;margin:4px;border:1px solid #ccd3da;border-radius:6px}button{cursor:pointer;background:#1769e0;color:white}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #e7ebef;padding:8px}.danger{background:#c62828}.muted{color:#66717d}pre{white-space:pre-wrap;max-height:260px;overflow:auto}</style></head>
<body><main><h1>录播达人授权管理</h1><section><label>管理令牌 <input id="token" type="password" size="48" autocomplete="off"></label><button onclick="loadLicenses()">登录 / 刷新</button><span id="status" class="muted"></span></section>
<section><h2>生成激活码</h2><input id="count" type="number" min="1" max="1000" value="10"><input id="note" placeholder="备注"><button onclick="batch()">生成</button><button onclick="downloadCodes()">导出 CSV</button><pre id="codes"></pre></section>
<section><h2>许可证</h2><input id="search" placeholder="ID、尾号或备注"><button onclick="loadLicenses()">搜索</button><table><thead><tr><th>尾号</th><th>状态</th><th>备注</th><th>绑定设备</th><th>操作</th></tr></thead><tbody id="rows"></tbody></table></section>
<section><h2>最近激活事件</h2><button onclick="loadEvents()">刷新事件</button><table><thead><tr><th>时间</th><th>类型</th><th>许可证</th><th>安装摘要</th></tr></thead><tbody id="events"></tbody></table></section>
<section><h2>版本配置</h2><input id="version" placeholder="版本号"><input id="url" size="42" placeholder="HTTPS 下载地址"><label><input id="mandatory" type="checkbox">强制更新</label><button onclick="saveVersion()">保存 stable</button></section>
</main><script>
let lastCodes=[]; const token=()=>document.querySelector('#token').value; const headers=()=>({'Content-Type':'application/json','Authorization':'Bearer '+token()});
async function api(path,options={}){options.headers=headers();const r=await fetch(path,options);if(!r.ok)throw new Error((await r.json()).message||r.statusText);return r.json()}
async function loadLicenses(){try{const q=encodeURIComponent(document.querySelector('#search').value);const xs=await api('/admin/licenses?search='+q);document.querySelector('#rows').innerHTML=xs.map(x=>'<tr><td>…'+esc(x.codeHint)+'</td><td>'+esc(x.status)+'</td><td>'+esc(x.note||'')+'</td><td>'+x.bindings.filter(b=>b.active).map(b=>esc(b.deviceFingerprintHash.slice(0,12))+'…').join('<br>')+' ('+x.bindings.filter(b=>b.active).length+'/'+x.maxDevices+')</td><td><button onclick="unbind(\''+x.id+'\')">解绑</button> <button class="danger" onclick="disable(\''+x.id+'\')">禁用</button></td></tr>').join('');status('已加载 '+xs.length+' 条')}catch(e){status(e.message)}}
async function loadEvents(){try{const xs=await api('/admin/events');document.querySelector('#events').innerHTML=xs.map(x=>'<tr><td>'+esc(new Date(x.createdAt).toLocaleString())+'</td><td>'+esc(x.type)+'</td><td>'+esc((x.licenseId||'').slice(0,12))+'</td><td>'+esc((x.installationHash||'').slice(0,12))+'</td></tr>').join('')}catch(e){status(e.message)}}
async function batch(){try{const x=await api('/admin/licenses/batch',{method:'POST',body:JSON.stringify({count:Number(document.querySelector('#count').value),note:document.querySelector('#note').value||undefined})});lastCodes=x.codes;document.querySelector('#codes').textContent=x.codes.map(v=>v.code).join('\n');await loadLicenses()}catch(e){status(e.message)}}
async function unbind(id){if(confirm('确认解绑此许可证的设备？')){await api('/admin/licenses/'+id+'/unbind',{method:'POST'});await loadLicenses()}}
async function disable(id){if(confirm('确认禁用此许可证？')){await api('/admin/licenses/'+id+'/disable',{method:'POST'});await loadLicenses()}}
async function saveVersion(){try{await api('/admin/versions/stable',{method:'PUT',body:JSON.stringify({version:document.querySelector('#version').value,downloadUrl:document.querySelector('#url').value||undefined,mandatory:document.querySelector('#mandatory').checked})});status('版本已保存')}catch(e){status(e.message)}}
function downloadCodes(){const csv='id,code\n'+lastCodes.map(x=>x.id+','+x.code).join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='licenses.csv';a.click()}
function esc(v){const d=document.createElement('div');d.textContent=v;return d.innerHTML}function status(v){document.querySelector('#status').textContent=v}
</script></body></html>`;

@Controller()
export class AdminPageController {
  @Get('admin')
  @Header('Content-Type', 'text/html; charset=utf-8')
  @Header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
  page() { return ADMIN_HTML; }
}
