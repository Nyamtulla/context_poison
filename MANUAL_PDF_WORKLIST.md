# Manual PDF download worklist

94 papers could not be retrieved automatically. All open-access routes were tried
(Semantic Scholar OA index, OpenAlex OA locations, arXiv by ID and by title match,
publisher OA patterns, DOI redirect resolution). The remainder sit behind publisher
bot-protection or paywalls — MDPI and ACM return HTTP 403 to any automated request,
so these need a browser session, ideally through KU library institutional access.

## Where to save

**Save every PDF into `data/papers/` using the exact `save as` filename below.**
The filename is how the extraction step finds the paper — a wrong name means the
paper stays invisible even though the file is on disk.

Once files are in place, run `python scripts/fetch_missing_pdfs.py` to re-verify
what is now present (it skips anything already on disk and re-writes the worklist),
then the six full-text fields still need to be extracted per paper
(`technical_summary`, `key_result`, `baselines_compared`, `stated_limitations`,
`models_evaluated`, `datasets_benchmarks`). That extraction pass is not yet
scripted — the original one was done by reading each paper — so hand it back to
Claude to run rather than expecting a command to do it.

Full list also in `data/registries/missing_pdfs_manual_worklist.csv`.

## IEEE Xplore — 47 paper(s)

_Use KU institutional access (library proxy or on-campus network)._

| Save as | Title | Year | DOI |
|---|---|---:|---|
| `b524141dae64dda2c8c6458e1b12a8fa05e8d8fa.pdf` | A Concise Review of Security Challenges and Protection for LLM-based Agents in | 2026 | [10.1109/asens69964.2026.11605296](https://doi.org/10.1109/asens69964.2026.11605296) |
| `0099c9c109c3516f0bf0d7d67502e99e86c78130.pdf` | A Modular Generative Honeypot Shell | 2024 | [10.1109/csr61664.2024.10679411](https://doi.org/10.1109/csr61664.2024.10679411) |
| `1ee66ccebe2e1c1d8f3f3ec74c957ea91dcd2e98.pdf` | A Multi-Agent Framework for Step-Level Tool-Call Safety Evaluation in Industri | 2026 | [10.1109/aiita69518.2026.11567230](https://doi.org/10.1109/aiita69518.2026.11567230) |
| `64db5497a9b02734cdb6766268ce8929d98c8c20.pdf` | A Reproducible Benchmark for Prompt Injection Vulnerability Assessment in Smal | 2025 | [10.1109/iccit68739.2025.11490549](https://doi.org/10.1109/iccit68739.2025.11490549) |
| `e21b1f9b29e0fc0671300eab00a762c316c19793.pdf` | A Systematic Literature Review of Prompt Injection Attacks in LLM-Integrated S | 2026 | [10.1109/access.2026.3700492](https://doi.org/10.1109/access.2026.3700492) |
| `8f899eda5a2d8df504d805dcf8d6e5dd9e15d68c.pdf` | Adversarial and Multilingual Threats in Retrieval-Augmented Generation: From P | 2025 | [10.1109/gaclm67198.2025.11231998](https://doi.org/10.1109/gaclm67198.2025.11231998) |
| `1bb6703e03c66fc8591d05cf1d2797a0b01757b7.pdf` | Alleviating Contextual Misguidance: Response-Aware Prompt Compression for Long | 2026 | [10.1109/taslpro.2026.3675784](https://doi.org/10.1109/taslpro.2026.3675784) |
| `e04cfb96e373bb30fdb3fa104843a9892b743f6a.pdf` | An Intent-Driven Task Graph Framework for Safe Long-Horizon Execution in Embod | 2026 | [10.1109/icmtim69588.2026.11526204](https://doi.org/10.1109/icmtim69588.2026.11526204) |
| `fb1bc7f717df24bef2a98d1dab26b0d86f069dd2.pdf` | AutoRed: Automated Attack Scenario Generation Framework for Red Teaming of LLM | 2024 | [10.1109/bigdata62323.2024.10825267](https://doi.org/10.1109/bigdata62323.2024.10825267) |
| `fb7d254c08e64bf3d793c837749936a7795bf9b9.pdf` | CKG-RAG: Enhancing LLM Reasoning in Medical Domain Using Contextual Knowledge  | 2026 | [10.1109/cscwd68734.2026.11582487](https://doi.org/10.1109/cscwd68734.2026.11582487) |
| `d3c9e1b9a6f4847efd8fd382fdb36e6a7536f655.pdf` | Chain-of-Memory: Taming Hallucinations in Million-Token Models with Verifiable | 2025 | [10.1109/icoabcd67551.2025.11470747](https://doi.org/10.1109/icoabcd67551.2025.11470747) |
| `1217aaf8b6fda0bc84a345feb611ce5b0edddd7a.pdf` | CoCortex: A Memory Governance Framework for Reliable Long-Horizon LLM Agents | 2026 | [10.1109/nelex69209.2026.11590154](https://doi.org/10.1109/nelex69209.2026.11590154) |
| `a96ec007ce6b034623afb6778eb67f99350b0c8d.pdf` | Controlled Benchmarking of Memory Topologies in LLM-Based Multi-Agent Systems: | 2026 | [10.1109/usbereit70063.2026.11580460](https://doi.org/10.1109/usbereit70063.2026.11580460) |
| `5fd47f3c351347de692aa41262acd331635f5879.pdf` | Cross-Agent Multimodal Provenance-Aware Framework for Robust Prompt Injection  | 2025 | [10.1109/icca66035.2025.11430791](https://doi.org/10.1109/icca66035.2025.11430791) |
| `fb29863cb5ac9458f84db8430d69727acf115361.pdf` | Designing and Verifying Agentic AI Systems through Structural Architecture and | 2026 | [10.1109/icst69053.2026.00013](https://doi.org/10.1109/icst69053.2026.00013) |
| `faeeeae11b73d012ddaa942a9d496b3109861f87.pdf` | Eliminating Retrieval Knowledge Conflicts: Cross-Validation Re-ranking with La | 2025 | [10.1109/ijcnn64981.2025.11228012](https://doi.org/10.1109/ijcnn64981.2025.11228012) |
| `141d242563718b4677b350f6a89fd28172de1845.pdf` | Enterprise Search Portals: Hybrid RAG at Scale for Compliance-Sensitive Knowle | 2026 | [10.1109/iciice69672.2026.11565414](https://doi.org/10.1109/iciice69672.2026.11565414) |
| `af9f3b394a50bcbe1026685e991923d771c5608f.pdf` | Evaluating and Exploiting Security Vulnerabilities in Large Language Models (L | 2025 | [10.1109/iccpct65132.2025.11176591](https://doi.org/10.1109/iccpct65132.2025.11176591) |
| `341883c91dabb788b32dae7d1bd6c6146d266b95.pdf` | Failure-Gated Hierarchical Memory: Preventing Memory Pollution in Long-Horizon | 2026 | [10.1109/mlise70044.2026.11607496](https://doi.org/10.1109/mlise70044.2026.11607496) |
| `e446aa098e37f3969e1cde7101959575f46fec56.pdf` | Forensic LLM-Trace: Interpretable Multi-Agent AI Forensic Architecture for Pro | 2026 | [10.1109/icscan66520.2026.11588474](https://doi.org/10.1109/icscan66520.2026.11588474) |
| `0b8b141e8d1300b9b8910aecb4617c66b2127417.pdf` | IDE-Sanitizer: A Prompt-Injection Cryptographic Context Guard for IDE Copilots | 2026 | [10.1109/smartnets69662.2026.11604974](https://doi.org/10.1109/smartnets69662.2026.11604974) |
| `d4cc36f9d0a6674c77c91a3c88dc2c71aa4e6340.pdf` | IEI-TIA: Industrial Embodied Intelligence Trustworthy Interpretable Agent for  | 2026 | [10.1109/tase.2026.3687369](https://doi.org/10.1109/tase.2026.3687369) |
| `ded623e9150e26bd567f5400ca581f070fcd5658.pdf` | Interaction-Centric Cybersecurity Risks in LLM-Powered Dialogue Systems | 2026 | [10.1109/ccwc67433.2026.11393850](https://doi.org/10.1109/ccwc67433.2026.11393850) |
| `3a18c13c43cea82a48860682dae5c5a6822d6b34.pdf` | LLM-PEA: Leveraging Large Language Models Against Phishing Email Attacks | 2026 | [10.1109/dsn-w70714.2026.00038](https://doi.org/10.1109/dsn-w70714.2026.00038) |
| `8fbbfece62a5d9dcb4e5bc7478c72b31e3ef80d6.pdf` | Manufacturing Domain QA with Integrated Term Enhanced RAG | 2024 | [10.1109/ijcnn60899.2024.10649905](https://doi.org/10.1109/ijcnn60899.2024.10649905) |
| `dc05567166d3f4504978a6e1728bbd24a972805c.pdf` | MedRAGShield: A Three-Tier Defense Framework Against Document Poisoning and Ad | 2026 | [10.1109/icesst69086.2026.11582854](https://doi.org/10.1109/icesst69086.2026.11582854) |
| `06fa2b9d40f97bd093aa3d21f42828ed82d8f55e.pdf` | Meticulous Thought Defender: Fine-Grained Chain-of-Thought (CoT) for Detecting | 2025 | [10.1109/access.2025.3583759](https://doi.org/10.1109/access.2025.3583759) |
| `1bab99ecc468fa9d84f06e405eeacaf9bf86e76f.pdf` | Mitigating Context Loss in Legal RAG: A Metadata-Aware Chunking Strategy for H | 2026 | [10.1109/ickecs70176.2026.11528014](https://doi.org/10.1109/ickecs70176.2026.11528014) |
| `08b698dcb67ab586a043d4dc5c14e55ba6b7f51f.pdf` | Multimodal Prompt Injection: A Formal 4D Taxonomy for Image and Document Pipel | 2026 | [10.1109/qpain69676.2026.11545895](https://doi.org/10.1109/qpain69676.2026.11545895) |
| `c3e90e9c5afbadac2114e97101b695a8c6b9bff5.pdf` | PRISM: Prompt Red-teaming and Injection Simulation for Models – A Scalable Fra | 2026 | [10.1109/icsft66733.2026.11508065](https://doi.org/10.1109/icsft66733.2026.11508065) |
| `2e511f5d91f1749659fd4980c586f9161532b156.pdf` | Prompting for LLM Security and RAG: A Survey from Zero-Shot to Automatic Promp | 2026 | [10.1109/icaic67076.2026.11395889](https://doi.org/10.1109/icaic67076.2026.11395889) |
| `4f6bc1797993f1ff1ddb1fccb9111bc424fa2242.pdf` | RAG-Induced Failures in Multi-Agent Large Language Model Debate | 2026 | [10.1109/icetes68504.2026.11518808](https://doi.org/10.1109/icetes68504.2026.11518808) |
| `43706cbea8b3d68e48173070a95b7bb5073ad225.pdf` | RIPE-II: Retrieval In-Place Poisoning Evaluation with Indirect Injections | 2026 | [10.1109/dsn69566.2026.00078](https://doi.org/10.1109/dsn69566.2026.00078) |
| `0ca1b5ccfc5cc3aeb869f45654dd7fa7fed3e188.pdf` | SHIELD: Security against Harmful Prompt Injection Evaluation and Language Dete | 2025 | [10.1109/iecon58223.2025.11221566](https://doi.org/10.1109/iecon58223.2025.11221566) |
| `08e6079c73649ba405826d9ea5da1c18645fcdb6.pdf` | Secure Prompt Engineering Patterns for Cloud LLM Agents | 2026 | [10.1109/icaic67076.2026.11395764](https://doi.org/10.1109/icaic67076.2026.11395764) |
| `d65ba82f774f67790912d003539354155e7ff91c.pdf` | Secure by Design: Quantifying Architectural Resilience and the Agents Rule of  | 2026 | [10.1109/southeastcon63549.2026.11475941](https://doi.org/10.1109/southeastcon63549.2026.11475941) |
| `3f47521e7f448d514a02d341f4cc5d71341cc884.pdf` | SecurePrompt – Detecting and Mitigating Prompt Attacks | 2025 | [10.1109/icccmla66092.2025.11581051](https://doi.org/10.1109/icccmla66092.2025.11581051) |
| `c157f40ed322da549b9fe31de69b4fb81428d9ce.pdf` | SecureRag: Preventing Sensitive Information Leakage In Rag Pipelines | 2025 | [10.1109/ic2sdt68218.2025.11383622](https://doi.org/10.1109/ic2sdt68218.2025.11383622) |
| `96501f13d4c7a2da1228220c5723098e54f63a7c.pdf` | Security-Aware Retrieval-Augmented Generation System for Post-Quantum Cryptogr | 2026 | [10.1109/southeastcon63549.2026.11476026](https://doi.org/10.1109/southeastcon63549.2026.11476026) |
| `62cd3a8f6ca307517456320009962a71487666f2.pdf` | ShadowPlay: Engineering Defenses Against Role-Based Prompt Injection and Depen | 2025 | [10.1109/cyber-ai66431.2025.11233258](https://doi.org/10.1109/cyber-ai66431.2025.11233258) |
| `900d5304c3371bcedef4d7280da3bf326032202d.pdf` | Site Isolation is Dead: How Site Isolation is Broken in Agentic Browsers and E | 2026 | [10.1109/sp63933.2026.00241](https://doi.org/10.1109/sp63933.2026.00241) |
| `8cfd7609a0a41d7d462229d1b010afba148771a8.pdf` | Temporal Dynamics of Memory Poisoning in Web3-Style LLM Agents | 2026 | [10.1109/access.2026.3693560](https://doi.org/10.1109/access.2026.3693560) |
| `74bf328bb86c119e6282744c2badd79f5bb14f53.pdf` | Trust-Aware Orchestration Architecture for LLM-Assisted Workflows in Multi-Ten | 2026 | [10.1109/access.2026.3706063](https://doi.org/10.1109/access.2026.3706063) |
| `21e45f760e4f375bf0d68e41a4a9b71c46594b62.pdf` | Trust-Aware Runtime Verification for Autonomous LLM Agent Systems | 2026 | [10.1109/icaiset66439.2026.11541707](https://doi.org/10.1109/icaiset66439.2026.11541707) |
| `850cf7b5ab3e5cb879cfbb3421b7e220044777f5.pdf` | Visual and Structural Prompt Injection in Medical Rag Systems: a Comparative R | 2026 | [10.1109/ichora69329.2026.11536987](https://doi.org/10.1109/ichora69329.2026.11536987) |
| `a3be45ad07ac98246029dc5c0a504f9314eec5b6.pdf` | Zero-Shot Tokenizer Transfer for Targeted Attacks on Retrieval-Augmented Gener | 2026 | [10.1109/icaic67076.2026.11395696](https://doi.org/10.1109/icaic67076.2026.11395696) |
| `9aa8ef5683aa8f81d3e0a826c076b45ff0f2d270.pdf` | [Short Paper] Forensic Analysis of Indirect Prompt Injection Attacks on LLM Ag | 2024 | [10.1109/tps-isa62245.2024.00053](https://doi.org/10.1109/tps-isa62245.2024.00053) |

## Other / unknown publisher — 16 paper(s)

| Save as | Title | Year | DOI |
|---|---|---:|---|
| `777c3fb3234532eab31bc6dc9a3388c67f163f81.pdf` | An Empirical Evaluation of Prompt Injection Detection and Refusal-Usefulness T | 2025 | [10.63575/cia.2025.30205](https://doi.org/10.63575/cia.2025.30205) |
| `a89c73e617861763bf122d19a412c5700990d287.pdf` | Analisis Kualitatif Kerentanan AI Agent terhadap Serangan Prompt Injection dan | 2026 | [10.55606/juitik.v6i2.2369](https://doi.org/10.55606/juitik.v6i2.2369) |
| `d54a0c6f9163bbb01306417b426be49fc30db65b.pdf` | Beyond Injection Detection: A Positive-Security Prompt Firewall that Closes th | 2026 | [10.64898/2026.06.04.26354950](https://doi.org/10.64898/2026.06.04.26354950) |
| `f3dd32f7ab427e5b4998fe451aabb929a324755c.pdf` | Cascading Instruction Influence Indirect Prompt Injection in Hierarchical Mult | 2026 | [10.19139/soic-2310-5070-3574](https://doi.org/10.19139/soic-2310-5070-3574) |
| `a74a834354664273b3dda00602f211df7563ad6c.pdf` | Cross-layer contagion of prompt injections in multi-agent swarms: a multiplex  | 2026 | [10.1186/s42400-026-00628-w](https://doi.org/10.1186/s42400-026-00628-w) |
| `b36a1f6cbc8ffb54b5f694328fa732a1bf1bc617.pdf` | Master’s Thesis Network Forensics, 60 credits A Hybrid Defense Against Prompt  | ? | https://www.semanticscholar.org/paper/b36a1f6cbc8ffb54b5f694328fa732a1bf1bc617 |
| `2605.13631.pdf` | ProjGuard: Safety Monitoring for Computer-Use Agents via Low-Dimensional Proje | 2026 | https://www.semanticscholar.org/paper/45c41693ece0aebf5d9210aa3a983046ee325c65 |
| `f201926c2fcd7f172dd8370392c39699ea46d093.pdf` | Prompt Injection Attacks on Large Language Models: Multi-Model Security Analys | 2025 | [10.5220/0013838400004000](https://doi.org/10.5220/0013838400004000) |
| `1c8b199b9868dc1275c7a275aff2e2fe3858925d.pdf` | Research and Analysis on the Mechanism of Suppressing Large Model Hallucinatio | 2026 | [10.54097/bp841717](https://doi.org/10.54097/bp841717) |
| `aef8626298e9cc4baf45000697e61626552fc2e4.pdf` | Retrieval Augmentation Reduces Factual Errors in Knowledge-Intensive Language  | 2026 | [10.54097/8jvwpk07](https://doi.org/10.54097/8jvwpk07) |
| `dd42a440316cbae44b0ff68fe79914b07799a8ec.pdf` | Securing the Boundary: Trust Context Separation in Privileged AI Agent Systems | 2026 | [10.52710/cfs.1012](https://doi.org/10.52710/cfs.1012) |
| `88b9628dee420a94c63fe3f0ec6b01fdc930e8d8.pdf` | Self-Healing Memory Architectures for Large Language Model-Based Multi-Agent C | 2026 | [10.71465/ajainn3659](https://doi.org/10.71465/ajainn3659) |
| `0cb61ce2a348d044ae0d4ad5d9acc05daa1e7776.pdf` | Systematically Analysing Prompt Injection Vulnerabilities in Diverse LLM Archi | 2025 | [10.34190/iccws.20.1.3292](https://doi.org/10.34190/iccws.20.1.3292) |
| `ca09b6c6b7233a4547d59841cffa115a083d9121.pdf` | The Comprehensive Review on Prompt Injection Attacks and Defense Mechanisms in | 2025 | [10.61173/390f5h97](https://doi.org/10.61173/390f5h97) |
| `f77c949f1b9101854b62aabf0da5ae887df18b8b.pdf` | Verlog: Context-lite Multi-turn Reinforcement Learning framework for Long-Hori | ? | https://www.semanticscholar.org/paper/f77c949f1b9101854b62aabf0da5ae887df18b8b |
| `bcc321fb567cfe7378d37a260be004f23617f080.pdf` | Vulnerabilities and Risk Analysis of Multi-Agentic AI-RAG in Autonomous Vehicl | 2026 | [10.24018/ejai.2026.5.1.1094](https://doi.org/10.24018/ejai.2026.5.1.1094) |

## ACM Digital Library — 15 paper(s)

_Use KU institutional access (library proxy or on-campus network)._

| Save as | Title | Year | DOI |
|---|---|---:|---|
| `2c6f684a777a194f3dff92d3014f2887b6bb6880.pdf` | Benchmarking Serverless AI Architectures: Modular RAG, Serverless RAG, and Lon | 2026 | [10.1145/3809481.3816479](https://doi.org/10.1145/3809481.3816479) |
| `dc27c98b0f700f4a55fe726e6eae23f90834cd7a.pdf` | BordaRAG: Resolving Knowledge Conflict in Retrieval-Augmented Generation via B | 2025 | [10.1145/3746252.3761038](https://doi.org/10.1145/3746252.3761038) |
| `01a8565a4529187bf9b51f28f0959f00a4fe8fd5.pdf` | Conflict-Aware RAG: Multi-Stage Learning with Conflict Signals for Robust Retr | 2026 | [10.1145/3774904.3792289](https://doi.org/10.1145/3774904.3792289) |
| `653ca4825ad48531899871aa40c59300b6b97823.pdf` | Context Viewer: Turning LLM Contexts into Analyzable Artifacts | 2026 | [10.1145/3786335.3813210](https://doi.org/10.1145/3786335.3813210) |
| `6db401bb9e8afddf06290f64b9d0df7a67719ca3.pdf` | Decomposition, Think and Action: Alleviating Hallucinations of Large Language  | 2026 | [10.1145/3827609](https://doi.org/10.1145/3827609) |
| `32743a56cf5a28f45d9fdf237450095b1ec9efe9.pdf` | Ebbinghaus Forgetting Curve and Large Language Model Memory Management: A Cogn | 2026 | [10.1145/3803291.3803294](https://doi.org/10.1145/3803291.3803294) |
| `f5fa4852ded771092858856b14f0f59443479be5.pdf` | MCP-Scanner: Detecting Security Risks in Model Context Protocol Systems | 2026 | [10.1145/3786160.3788471](https://doi.org/10.1145/3786160.3788471) |
| `057aa5b70532227a3eb2710604d328b7486f8561.pdf` | Multi-Agent AI Framework for Threat Mitigation and Resilience in Machine Learn | 2026 | [10.1145/3780095](https://doi.org/10.1145/3780095) |
| `a00030f261b800f4156c88d01e0173f872962b99.pdf` | OPENCLAW-SRT: Resource-Aware Autonomous Agent Architecture for Smart City Edge | 2026 | [10.1145/3821835.3821917](https://doi.org/10.1145/3821835.3821917) |
| `069e9bd355c20013de5224be1324a57a4a14352f.pdf` | Poster: Agentic Shell Honeypot Using Structured Logging | 2025 | [10.1145/3719027.3760731](https://doi.org/10.1145/3719027.3760731) |
| `e2e5529df48fe6cf893da483360958b32d829724.pdf` | SecureGov-Agent: A Governance-Centric Multi-Agent Framework for Privacy-Preser | 2025 | [10.1145/3795154.3795296](https://doi.org/10.1145/3795154.3795296) |
| `927b5bd48e1210d752b8e7ce437afa8f5cc2bcdd.pdf` | Towards Large Language Model (LLM) Forensics Using LLM-based Invocation Log An | 2023 | [10.1145/3689217.3690616](https://doi.org/10.1145/3689217.3690616) |
| `b7f22c242732ccba8be3c1f5484af4f5032a0d83.pdf` | TraceCaps: Inline Provenance and Risk Enforcement for Agentic Software Enginee | 2026 | [10.1145/3786582.3786832](https://doi.org/10.1145/3786582.3786832) |
| `74aec0665c948c64072682901b7e95e7b71286e4.pdf` | WAB: Overcoming Memory, Network, and Security Walls in Native Agentic Browsers | 2026 | [10.1145/3774905.3795093](https://doi.org/10.1145/3774905.3795093) |
| `f6bc99088f51e29efb6af663a30ab26f74063309.pdf` | Weaponizing Words: Direct & Indirect Prompt Injection Attacks on LLM | 2025 | [10.1145/3769694.3771165](https://doi.org/10.1145/3769694.3771165) |

## MDPI (open access) — 12 paper(s)

_Open access — no subscription needed, just a browser._

| Save as | Title | Year | DOI |
|---|---|---:|---|
| `0388c22f0b2a9650d202ab8ccb445fb8af730f1e.pdf` | Detecting Prompt Injection Attacks in Generative AI Systems: A Hybrid SIEM and | 2026 | [10.3390/electronics15112242](https://doi.org/10.3390/electronics15112242) |
| `dfc9d7ad54c197d239cb473f3ae7a64ab50d0e90.pdf` | Embedding-Based Detection of Indirect Prompt Injection Attacks in Large Langua | 2026 | [10.3390/a19010092](https://doi.org/10.3390/a19010092) |
| `4d4bcd13ba6241c38abe4f49db5045d6311526b1.pdf` | Federated Retrieval-Augmented Generation for Cybersecurity in Resource-Constra | 2026 | [10.3390/electronics15071409](https://doi.org/10.3390/electronics15071409) |
| `af911725f2032ad6b8cb7d5c01fd7fb6e404e4ef.pdf` | LLM Firewall Using Validator Agent for Prevention Against Prompt Injection Att | 2025 | [10.3390/app16010085](https://doi.org/10.3390/app16010085) |
| `bd8d64d442ec88eaf5c3117e3700e61021db0587.pdf` | Mind Mapping Prompt Injection: Visual Prompt Injection Attacks in Modern Large | 2025 | [10.3390/electronics14101907](https://doi.org/10.3390/electronics14101907) |
| `32aa80580c3152691ade3ce65f523ee15948312a.pdf` | Multi-Layered Framework for LLM Hallucination Mitigation in High-Stakes Applic | 2025 | [10.3390/computers14080332](https://doi.org/10.3390/computers14080332) |
| `986fc8d841425a81947838425ea292685ef8325a.pdf` | Multi-Route Search and Adaptive Fusion for Power QA with Small Language Model  | 2026 | [10.3390/a19050378](https://doi.org/10.3390/a19050378) |
| `title_fc1fc8c2fc85deb5.pdf` | Prompt Injection Attacks in Large Language Models and AI Agent Systems: A Comp | 2026 | [10.3390/info17010054](https://doi.org/10.3390/info17010054) |
| `ebd1f47a013b7b488bef0ddbf500bd0423c345ba.pdf` | Prompt Injection Attacks in Large Language Models and AI Agent Systems: A Comp | 2026 | [10.3390/info17010054](https://doi.org/10.3390/info17010054) |
| `3fdd6bd75acec6e9e54a439a0f8c878c3656397f.pdf` | PromptSentinel-X: A Leakage-Aware and Context-Aware Framework for Prompt-Injec | 2026 | [10.3390/fi18070376](https://doi.org/10.3390/fi18070376) |
| `0f6b86356acc0b2a172096bda2193a6026986628.pdf` | Runtime Policy Enforcement for MCP-Based LLM Agents | 2026 | [10.3390/electronics15132829](https://doi.org/10.3390/electronics15132829) |
| `c0de209bae19d27807acc85538f8deafbde4390a.pdf` | Security and Privacy of Large Language Models: Threat Taxonomy, Ethical Implic | 2026 | [10.3390/ai7050152](https://doi.org/10.3390/ai7050152) |

## arXiv — 2 paper(s)

| Save as | Title | Year | DOI |
|---|---|---:|---|
| `2601.07853.pdf` | FinVault: Benchmarking Financial Agent Safety in Execution-Grounded Environmen | 2026 | [10.48550/arxiv.2601.07853](https://doi.org/10.48550/arxiv.2601.07853) |
| `2602.17547.pdf` | KLong: Training LLM Agent for Extremely Long-horizon Tasks | 2026 | [10.48550/arxiv.2602.17547](https://doi.org/10.48550/arxiv.2602.17547) |

## Springer — 1 paper(s)

_Use KU institutional access (library proxy or on-campus network)._

| Save as | Title | Year | DOI |
|---|---|---:|---|
| `deb43c5a66d7188b4a83af3dc6d9b1b7a02fc302.pdf` | Indirect prompt injection in large language models | 2026 | [10.1007/s00521-026-12266-x](https://doi.org/10.1007/s00521-026-12266-x) |

## Elsevier — 1 paper(s)

_Use KU institutional access (library proxy or on-campus network)._

| Save as | Title | Year | DOI |
|---|---|---:|---|
| `27f8e33cf5eac88b85aabb2e9f9d6e6114cf2cbe.pdf` | Thought Management System for long-horizon, goal-driven LLM agents | 2025 | [10.1016/j.jocs.2025.102740](https://doi.org/10.1016/j.jocs.2025.102740) |
