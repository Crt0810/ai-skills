# 常用网站域名分组（按类别批量配置直连/代理）

用户要求"给某类网站配置直连/代理"时，从下表挑选域名，用 `add_rules.py` 批量添加。策略仅为建议，按用户网络实际情况调整。

## 学术文献/期刊（建议：直连 DIRECT）

| 域名 | 覆盖站点 |
|---|---|
| aps.org | PRL / PRA / PRX / PRX Quantum / PRR / Reviews of Modern Physics 等全部 APS 期刊 |
| nature.com | Nature 及 Nature 系列、npj、Scientific Reports |
| science.org | Science / Science Advances |
| iop.org | IOP 系列（New J. Phys. / J. Phys. A / RPP / QST 等，含 iopscience.iop.org） |
| scipost.org | SciPost |
| quantum-journal.org | Quantum 开放期刊 |
| sciencedirect.com | Elsevier（Optics Communications / Results in Physics 等） |
| springer.com | Springer（含 link.springer.com） |
| tandfonline.com | Taylor & Francis |
| opg.optica.org | Optica / Optics Express |
| ieee.org | IEEE（含 ieeexplore.ieee.org） |
| aip.org | AIP（Rev. Sci. Instrum. / Am. J. Phys.） |
| wiley.com | Wiley |
| arxiv.org | arXiv 预印本 |
| doi.org / crossref.org | DOI 跳转与元数据（强烈建议一并直连，否则点击 DOI 先走代理） |
| ncbi.nlm.nih.gov / pubmed.ncbi.nlm.nih.gov | PubMed / NCBI |
| semanticscholar.org | Semantic Scholar |

## AI 服务（通常建议：走代理 PROXY）

| 域名 | 覆盖站点 |
|---|---|
| openai.com / chatgpt.com / oaistatic.com | ChatGPT / OpenAI |
| gemini.google.com / aistudio.google.com / deepmind.com | Gemini / AI Studio |
| anthropic.com / claude.ai | Claude |
| x.ai / grok.com | xAI / Grok |
| perplexity.ai | Perplexity |
| github.com / raw.githubusercontent.com | GitHub（代码访问建议代理） |

## 社交/内容平台（按用户需求）

| 域名 | 说明 |
|---|---|
| youtube.com / googlevideo.com / ytimg.com | YouTube（一般走代理） |
| x.com / twitter.com | X/Twitter |
| instagram.com / facebook.com | Instagram / Facebook |
| tiktok.com | TikTok |
| reddit.com | Reddit |
| wikipedia.org | 维基百科（国内需代理，视网络） |

## 常用工具/开发

| 域名 | 说明 |
|---|---|
| google.com / googleapis.com / gstatic.com | Google 系 |
| stackoverflow.com / stackexchange.com | 开发者问答 |
| npmjs.com / registry.npmjs.org | npm |
| pypi.org / files.pythonhosted.org | PyPI（直连或代理按网络实测） |
| docker.io / docker.com | Docker Hub |
| microsoft.com / msn.com | 微软系（多数可直连） |

## 使用提示

- 直接按需挑选即可，例如：`python add_rules.py --direct aps.org nature.com arxiv.org doi.org --proxy youtube.com github.com`
- 国内可直连站点（百度、B站、知乎、淘宝等）通常订阅已内置 `GEOIP,CN,DIRECT` 处理，无需手动添加。
- 不确定某站直连是否可用时，先只加一条并实测，不通再删除或改代理。
