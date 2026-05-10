from typing import Any


def hot_list() -> dict[str, Any]:
    return {
        "Code": 0,
        "Message": "success",
        "Data": {
            "Total": 2,
            "Items": [
                {
                    "Title": "AI 编程工具会不会改变程序员的成长路径？",
                    "Url": "https://www.zhihu.com/question/123456789",
                    "ThumbnailUrl": "https://pic1.zhimg.com/mock.jpg",
                    "Summary": "讨论集中在 AI 是否压缩初级岗位，以及程序员是否需要调整训练方式。",
                },
                {
                    "Title": "Agent Quality 到底评估什么？",
                    "Url": "https://zhuanlan.zhihu.com/p/987654321",
                    "ThumbnailUrl": "",
                    "Summary": "围绕任务完成率、工具调用、上下文管理和可观测性展开。",
                },
            ],
        },
    }


def zhihu_search(query: str, count: int) -> dict[str, Any]:
    return {
        "Code": 0,
        "Message": "success",
        "Data": {
            "HasMore": False,
            "SearchHashId": "mock-search-hash",
            "Items": [
                {
                    "Title": f"{query}：知乎高质量讨论",
                    "ContentType": "Article",
                    "ContentID": "mock-zhihu-search-001",
                    "ContentText": "代码生成正在成为基础能力，真正需要讨论的是工程上下文、研发流程和团队协作数据。",
                    "Url": "https://zhuanlan.zhihu.com/p/mock-001",
                    "CommentCount": 15,
                    "VoteUpCount": 128,
                    "AuthorName": "看山测试作者",
                    "AuthorAvatar": "https://picx.zhimg.com/mock-avatar.jpg",
                    "AuthorBadge": "",
                    "AuthorBadgeText": "",
                    "EditTime": 1748355858,
                    "CommentInfoList": [{"Content": "上下文是否能成为壁垒，关键看企业流程接入。"}],
                    "AuthorityLevel": "2",
                    "RankingScore": 0.98,
                }
            ][:count],
        },
    }


def global_search(query: str, count: int) -> dict[str, Any]:
    return {
        "Code": 0,
        "Message": "success",
        "Data": {
            "HasMore": False,
            "Items": [
                {
                    "Title": f"{query}：全网观点补充",
                    "ContentType": "Answer",
                    "ContentID": "mock-global-search-001",
                    "ContentText": "这个话题的关键不是<em>单次生成</em>，而是系统能不能进入真实研发链路。",
                    "Url": "https://www.zhihu.com/answer/mock-001",
                    "CommentCount": 22,
                    "VoteUpCount": 18,
                    "AuthorName": "知乎用户",
                    "AuthorAvatar": "https://picx.zhimg.com/mock-avatar.jpg",
                    "AuthorBadge": "",
                    "AuthorBadgeText": "",
                    "EditTime": 1748355858,
                    "CommentInfoList": [{"Content": "别忽略权限和审计。"}],
                    "AuthorityLevel": "2",
                }
            ][:count],
        },
    }


def ring_detail() -> dict[str, Any]:
    return {
        "status": 0,
        "msg": "success",
        "data": {
            "ring_info": {
                "ring_id": "2029619126742656657",
                "ring_name": "黑客松脑洞补给站",
                "ring_desc": "黑客松讨论圈",
                "ring_avatar": "https://pica.zhimg.com/mock.jpg",
                "membership_num": 100,
                "discussion_num": 42,
            },
            "contents": [
                {
                    "pin_id": 1992912496017834773,
                    "title": "AI Agent 黑客松脑洞",
                    "content": "我们正在讨论读写一体创作 Agent。",
                    "author_name": "看山测试作者",
                    "images": [],
                    "publish_time": 1767928220,
                    "like_num": 12,
                    "comment_num": 3,
                    "share_num": 0,
                    "fav_num": 2,
                    "comments": [
                        {
                            "comment_id": 11388555101,
                            "content": "<p>这个方向适合强调观点形成过程。</p>",
                            "author_name": "测试评论者",
                            "author_token": "mock-user",
                            "like_count": 4,
                            "reply_count": 0,
                            "publish_time": 1767949522,
                        }
                    ],
                }
            ],
        },
    }


def comments() -> dict[str, Any]:
    return {
        "status": 0,
        "msg": "success",
        "data": {
            "comments": [
                {
                    "comment_id": "11387042978",
                    "content": "<p>这篇文章还需要更多真实案例。</p>",
                    "author_name": "读者 A",
                    "author_token": "reader-a",
                    "like_count": 8,
                    "reply_count": 1,
                    "publish_time": 1767949522,
                    "reply_to": "",
                }
            ]
        },
    }


def story_list() -> dict[str, Any]:
    return {
        "status": 0,
        "msg": "success",
        "data": [
            {
                "work_id": "1644038836790169600",
                "title": "秦始皇登月计划",
                "artwork": "https://picx.zhimg.com/mock-story.jpg",
                "tab_artwork": "https://picx.zhimg.com/mock-story-tab.jpg",
                "description": "历史脑洞故事简介",
                "labels": ["史脑洞"],
            }
        ],
    }


def story_detail(work_id: str) -> dict[str, Any]:
    return {
        "status": 0,
        "msg": "success",
        "data": {
            "work_id": work_id,
            "chapter_name": "秦始皇登月计划",
            "author_avatar": "https://picx.zhimg.com/mock-author.jpg",
            "author_name": "六酒",
            "labels": ["史脑洞"],
            "introduction": "导语文本",
            "content": "第一段正文\n第二段正文",
        },
    }


def following_feed() -> dict[str, Any]:
    return {
        "data": [
            {
                "actor": {"name": "关注作者"},
                "action_text": "回答了问题",
                "action_time": 1767928220,
                "target": {
                    "title": "AI Coding 产品正在从插件走向工作流入口",
                    "excerpt": "未来竞争点不是补全几行代码，而是谁能进入需求、开发、测试和发布链路。",
                    "author": {"name": "关注作者"},
                },
            }
        ]
    }


def direct_answer(model: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 1740470400,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "reasoning_content": "先区分事实判断和价值判断。",
                    "content": "这个问题需要拆成模型能力、工程上下文和组织流程三层回答。",
                },
                "finish_reason": "stop",
            }
        ],
    }
