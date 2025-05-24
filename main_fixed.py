# bazi_server.py - 修复版本

from flask import Flask, request, jsonify, send_file
from datetime import datetime, timedelta, date
from lunar_python import Solar, LunarYear
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return send_file("index.html")

def run_bazi_analysis(birth_datetime: datetime, gender: int, task: str, days: int, current_time: datetime) -> dict:
    """返回包含所有分析结果的字典"""
    result = {
        'prints': [],
        'data': {}
    }

    try:
        solar = Solar.fromDate(birth_datetime)
        lunar = solar.getLunar()
        bazi = lunar.getEightChar()
        bazi.setSect(1)

        # 基础信息
        gan_zhi_list = [bazi.getYear(), bazi.getMonth(), bazi.getDay(), bazi.getTime()]
        result['data']['gan_zhi'] = [str(gz) for gz in gan_zhi_list]
        result['prints'].append(f"干支列表: {gan_zhi_list}")

        # 纳音信息
        nayin = {
            'year': bazi.getYearNaYin(),
            'month': bazi.getMonthNaYin(),
            'day': bazi.getDayNaYin(),
            'time': bazi.getTimeNaYin()
        }
        result['data']['nayin'] = nayin
        result['prints'].append(f"纳音：年:{nayin['year']},月:{nayin['month']},日:{nayin['day']},时:{nayin['time']}")

        # 十神信息
        shishen_gan = {
            'year': bazi.getYearShiShenGan(),
            'month': bazi.getMonthShiShenGan(),
            'day': bazi.getDayShiShenGan(),
            'time': bazi.getTimeShiShenGan()
        }
        result['data']['shishen_gan'] = shishen_gan
        result['prints'].append(
            f"干十神：年:{shishen_gan['year']},月:{shishen_gan['month']},日:{shishen_gan['day']},时:{shishen_gan['time']}")

        shishen_zhi = {
            'year': bazi.getYearShiShenZhi(),
            'month': bazi.getMonthShiShenZhi(),
            'day': bazi.getDayShiShenZhi(),
            'time': bazi.getTimeShiShenZhi()
        }
        result['data']['shishen_zhi'] = shishen_zhi
        result['prints'].append(
            f"支十神：年:{shishen_zhi['year']},月:{shishen_zhi['month']},日:{shishen_zhi['day']},时:{shishen_zhi['time']}")

        # 强弱分析
        year_gz, month_gz, day_gz, time_gz = bazi.getYear(), bazi.getMonth(), bazi.getDay(), bazi.getTime()

        # 天干和五行映射
        gan_wuxing = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
                      "庚": "金", "辛": "金", "壬": "水", "癸": "水"}

        # 地支藏干映射（主+中+余气）
        zhi_canggan = {
            "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
            "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"], "午": ["丁", "己"],
            "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"], "酉": ["辛"],
            "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"]
        }

        # 初始化五行统计
        wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}

        # 统计天干
        for gz in gan_zhi_list:
            gan = str(gz)[0]
            if gan in gan_wuxing:
                wuxing_count[gan_wuxing[gan]] += 1

        # 统计藏干
        for gz in gan_zhi_list:
            zhi = str(gz)[1]
            if zhi in zhi_canggan:
                for gan in zhi_canggan[zhi]:
                    if gan in gan_wuxing:
                        wuxing_count[gan_wuxing[gan]] += 1

        # 日主
        day_gan = str(day_gz)[0]
        day_wuxing = gan_wuxing[day_gan]

        # 五行生克关系
        sheng_map = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}  # 我生
        ke_map = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}  # 我克
        sheng_wo = {v: k for k, v in sheng_map.items()}  # 生我
        ke_wo = {v: k for k, v in ke_map.items()}  # 克我

        # 三个维度判断强弱：得令、得地、得助
        month_zhi = str(month_gz)[1]
        de_ling = day_gan in zhi_canggan.get(month_zhi, [])

        other_zhi = [str(year_gz)[1], str(time_gz)[1]]
        de_di = any(
            day_gan in zhi_canggan.get(zhi, []) or sheng_wo.get(day_wuxing, '') in [gan_wuxing.get(g, '') for g in zhi_canggan.get(zhi, [])]
            for zhi in other_zhi
        )

        other_gan = [str(year_gz)[0], str(month_gz)[0], str(time_gz)[0]]
        de_zhu = any(
            gan_wuxing.get(gan) == day_wuxing or gan_wuxing.get(gan) == sheng_wo.get(day_wuxing)
            for gan in other_gan
        )

        # 强弱判断得分机制（0~3）
        strength_score = sum([de_ling, de_di, de_zhu])
        if strength_score >= 2:
            status = "日主偏强"
        elif strength_score == 1:
            status = "中和"
        else:
            status = "日主偏弱"

        # 用神与忌神判断
        if status == "日主偏强":
            yong_shen = [sheng_map[day_wuxing], ke_map[day_wuxing]]
            ji_shen = [day_wuxing, sheng_wo[day_wuxing]]
            xi_shen = ["--"]
        elif status == "日主偏弱":
            yong_shen = [day_wuxing, sheng_wo[day_wuxing]]
            ji_shen = [ke_map[day_wuxing], sheng_map[day_wuxing]]
            xi_shen = ["--"]
        else:
            # 中和格局
            sorted_wuxing = sorted(wuxing_count.items(), key=lambda x: x[1])
            xi_shen = [sorted_wuxing[0][0]]
            ji_shen = [sorted_wuxing[-1][0]]
            yong_shen = ["中庸调和"]

        qiangruo = {
            '日主': day_gan,
            '五行': day_wuxing,
            '日主强弱': status,
            '五行分布': wuxing_count,
            '用神': yong_shen,
            '喜神推荐': xi_shen,
            '忌神建议': ji_shen
        }
        result['data']['qiangruo'] = qiangruo
        result['prints'].append(
            f"\n【日主】：{day_gan}（五行：{day_wuxing}）\n【日主强弱】：{status}（得令：{de_ling}，得地：{de_di}，得助：{de_zhu}）\n【五行分布】：{wuxing_count}\n【用神推荐】：{yong_shen}\n【喜神推荐】：{xi_shen}\n【忌神建议】：{ji_shen}")

        # 大运分析
        yun = bazi.getYun(gender=gender, sect=2)
        dayun_arr = yun.getDaYun()

        # 存储大运基本信息
        result['data']['dayun'] = [{
            'index': d.getIndex(),
            'start_age': d.getStartAge(),
            'end_age': d.getEndAge(),
            'ganzhi': str(d.getGanZhi()),
            'start_year': d.getStartYear(),
            'end_year': d.getEndYear()
        } for d in dayun_arr]

        result['prints'].append("大运：")
        for d in dayun_arr:
            result['prints'].append(f"{d.getStartAge()}岁-{d.getEndAge()}岁：第{d.getIndex()}轮大运，{d.getGanZhi()}")

        # 计算当前年龄
        def calculate_age(birth: datetime, target: datetime) -> int:
            age = target.year - birth.year
            if (target.month, target.day) < (birth.month, birth.day):
                age -= 1
            return age

        age = calculate_age(birth_datetime, current_time)
        result['data']['current_age'] = age
        result['prints'].append(f"当前年龄: {age}岁")

        # 当前大运判断
        current_dayun = next((d for d in dayun_arr if d.getStartYear() <= current_time.year <= d.getEndYear()), None)
        
        if current_dayun:
            result['data']['current_dayun'] = {}
            result['data']['current_dayun']['basic'] = {
                'ganzhi': str(current_dayun.getGanZhi()),
                'age_range': f"{current_dayun.getStartAge()}~{current_dayun.getEndAge()}岁"
            }
            result['prints'].append(
                f"\n🎯 当前所在大运：{current_dayun.getGanZhi()} ({current_dayun.getStartAge()}~{current_dayun.getEndAge()}岁)")

            # 流年小运信息
            liu_nian_arr = current_dayun.getLiuNian()
            xiao_yun_arr = current_dayun.getXiaoYun()

            # 存储流年小运
            result['data']['current_dayun']['liunian'] = [{
                'year': ln.getYear(),
                'ganzhi': str(ln.getGanZhi())
            } for ln in liu_nian_arr]

            result['data']['current_dayun']['xiaoyun'] = [{
                'year': xy.getYear(),
                'ganzhi': str(xy.getGanZhi())
            } for xy in xiao_yun_arr]

            # 当前流月
            lunar_now = Solar.fromDate(current_time).getLunar()
            liu_yue_gz = lunar_now.getMonthInGanZhi()
            result['data']['current_dayun']['liuyue'] = str(liu_yue_gz)
            
            result['prints'].append(f"\n🗓 当前大运阶段的流年与小运：")
            for ln, xy in zip(liu_nian_arr, xiao_yun_arr):
                result['prints'].append(f"{ln.getYear()}年 | 流年：{ln.getGanZhi():<6} | 小运：{xy.getGanZhi()}")

            # 十神分析
            gan_yinyang = {"甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳", "己": "阴", 
                          "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴"}

            def get_ten_god(day_gan, other_gan):
                day_wx = gan_wuxing[day_gan]
                other_wx = gan_wuxing[other_gan]
                
                ten_god_map = {
                    ("同五行", "阳阳或阴阴"): "比肩",
                    ("同五行", "阴阳相异"): "劫财",
                    ("我生者", "阳阳或阴阴"): "食神",
                    ("我生者", "阴阳相异"): "伤官",
                    ("生我者", "阳阳或阴阴"): "正印",
                    ("生我者", "阴阳相异"): "偏印",
                    ("我克者", "阳阳或阴阴"): "正财",
                    ("我克者", "阴阳相异"): "偏财",
                    ("克我者", "阳阳或阴阴"): "正官",
                    ("克我者", "阴阳相异"): "七杀"
                }
                
                relation = ""
                if other_wx == day_wx:
                    relation = "同五行"
                elif sheng_map[day_wx] == other_wx:
                    relation = "我生者"
                elif sheng_wo[day_wx] == other_wx:
                    relation = "生我者"
                elif ke_map[day_wx] == other_wx:
                    relation = "我克者"
                elif ke_wo[day_wx] == other_wx:
                    relation = "克我者"
                else:
                    relation = "其他"

                yy_match = "阳阳或阴阴" if gan_yinyang[day_gan] == gan_yinyang[other_gan] else "阴阳相异"
                return ten_god_map.get((relation, yy_match), "未知")

            # 运势解释
            运势解释 = {
                "比肩": "自我强化之运，适合独立创业、自主决策",
                "劫财": "竞争压力之运，需注意合作关系与财务风险",
                "食神": "安逸享乐之运，适合创意表达、学术成长",
                "伤官": "才华释放之运，利于展示能力，需注意得罪权威",
                "正财": "稳健求财之运，适合投资理财、积累财富",
                "偏财": "偏门之财之运，适合接触机会型项目或跨界收益",
                "正官": "规范成长之运，适合晋升考试、公务申报等",
                "七杀": "压力挑战之运，利于突破瓶颈、展现领导力",
                "正印": "学习积累之运，利于深造、提升学历与资历",
                "偏印": "灵感与内省之运，适合研究、写作、静心修炼"
            }

            def interpret_ten_god(god):
                return 运势解释.get(god, "无明确运势")

            # 获取当前运势的十神
            da_yun_gan = str(current_dayun.getGanZhi())[0]
            
            # 找出当前年份对应的流年和小运
            liu_nian_gan = None
            xiao_yun_gan = None
            
            for ln, xy in zip(liu_nian_arr, xiao_yun_arr):
                if ln.getYear() == current_time.year:
                    liu_nian_gan = str(ln.getGanZhi())[0]
                    xiao_yun_gan = str(xy.getGanZhi())[0]
                    break

            liu_nian_gz = lunar_now.getYearInGanZhi()
            liu_yue_gan = str(liu_yue_gz)[0]
            
            da_yun_ten_god = get_ten_god(day_gan, da_yun_gan)
            xiao_yun_ten_god = get_ten_god(day_gan, xiao_yun_gan) if xiao_yun_gan else "未知"
            liu_nian_ten_god = get_ten_god(day_gan, str(liu_nian_gz)[0])
            liu_yue_ten_god = get_ten_god(day_gan, liu_yue_gan)

            # 运势解释
            a = f"\n【当前大运】：{current_dayun.getGanZhi()}（十神：{da_yun_ten_god}）→ {interpret_ten_god(da_yun_ten_god)}"
            b = f"【当前小运】：{xiao_yun_gan if xiao_yun_gan else '未知'}（十神：{xiao_yun_ten_god}）→ {interpret_ten_god(xiao_yun_ten_god)}"
            c = f"【当前流年】：{liu_nian_gz}（十神：{liu_nian_ten_god}）→ {interpret_ten_god(liu_nian_ten_god)}"
            d = f"【当前流月】：{liu_yue_gz}（十神：{liu_yue_ten_god}）→ {interpret_ten_god(liu_yue_ten_god)}"
            
            result['data']['current_dayun']['interpretations'] = {
                'dayun': a,
                'xiaoyun': b,
                'liunian': c,
                'liuyue': d
            }

            result['prints'].extend([a, b, c, d])

            # 定义学术/事业星含义
            career_star_meaning = {
                "食神": "适合创作、写作、享受学术带来的成果",
                "伤官": "利于发表、辩论、展示才华，需注意言辞锋芒",
                "正印": "利于学习考试、取得资质、师承、学位",
                "七杀": "适合突破压力挑战，有望脱颖而出"
            }

            # 判断学术/事业星是否出现
            career_stars = set(career_star_meaning.keys())
            active_stars = {
                "大运": da_yun_ten_god,
                "流年": liu_nian_ten_god,
                "流月": liu_yue_ten_god,
                "小运": xiao_yun_ten_god,
            }

            explan = {
                "大运": "周期：10年，十年一运，影响一个阶段的人生主线",
                "小运": "周期：1年，每年的岁运干支,直接对应当前年份，对应现实中发生的事件倾向和重点运势",
                "流年": "周期：1年，一年一运（随大运切换）,是大运的细化.",
                "流月": "周期：1月，每月的运势，代表短期趋势。"
            }

            # 提取出学术星曜所在的运势
            highlight = {k: v for k, v in active_stars.items() if v in career_stars}

            if highlight:
                print("\n🎯 当前对学术/事业发展较为有利，出现以下星曜：")
                for period, star in highlight.items():
                    meaning = career_star_meaning.get(star, "")
                    result['data']['current_dayun']['xingyao'] = {
                        'period': star,
                        'meaning':meaning,
                        'period_explanation': explan[period],
                    }
                    print(f" - 【{period}】出现金曜【{star}】：{meaning}.{period}:{explan[period]}")
                    result['prints'].extend(f" - 【{period}】出现金曜【{star}】：{meaning}.{period}:{explan[period]}")
            else:
                print("\n⚠️ 当前阶段对学术成就暂无显著激励星曜")
                result['prints'].extend(f"\n⚠️ 当前阶段对学术成就暂无显著激励星曜")

            # 择吉分析
            zhi_wuxing = {
                "子": "水", "丑": "土", "寅": "木", "卯": "木",
                "辰": "土", "巳": "火", "午": "火", "未": "土",
                "申": "金", "酉": "金", "戌": "土", "亥": "水"
            }

            def evaluate_day_for_task(date_obj, task, yongshen, jishen, day_gan, da_yun_ten_god, liu_nian_ten_god, liu_yue_ten_god):
                try:
                    solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
                    lunar = solar.getLunar()
                    day_gz = lunar.getDayInGanZhi()
                    day_gan_curr = str(day_gz)[0]
                    day_zhi_curr = str(day_gz)[1]
                    day_gan_wx = gan_wuxing.get(day_gan_curr, "未知")
                    day_zhi_wx = zhi_wuxing.get(day_zhi_curr, "未知")
                    
                    ji_shen_set = set(lunar.getDayJiShen())
                    xiong_sha_set = set(lunar.getDayXiongSha())

                    # 神煞评分表
                    task_yi_jishen = {
                        "投稿": {"文昌", "天乙", "学堂", "玉堂", "金匮", "月恩", "天德", "青龙"},
                        "返修": {"天德", "月德", "六合", "解神", "时德", "时阳", "天赦", "玉堂"},
                        "盲审": {"金匮", "天乙", "青龙", "明堂", "天恩", "天喜", "福生", "王日"},
                        "答辩": {"文昌", "三奇", "天喜", "金匮", "玉堂", "天医", "天赦", "明堂", "天德合"}
                    }

                    task_ji_xiongsha = {
                        "投稿": {"天贼", "披麻", "破日", "死神", "小耗", "月煞", "劫煞", "血忌"},
                        "返修": {"月破", "日破", "旬空", "天贼", "复日", "死气", "月厌", "月害"},
                        "盲审": {"披麻", "劫煞", "月煞", "死气", "五鬼", "天狗", "白虎"},
                        "答辩": {"天贼", "死气", "五鬼", "月厌", "朱雀", "地火", "白虎", "孤阳"}
                    }

                    score = 0
                    score += len(ji_shen_set.intersection(task_yi_jishen.get(task, set()))) * 1.5
                    score -= len(xiong_sha_set.intersection(task_ji_xiongsha.get(task, set()))) * 2

                    # 用神与忌神评分
                    if day_gan_wx in yongshen:
                        score += 2
                    if day_zhi_wx in yongshen:
                        score += 1
                    if day_gan_wx in jishen:
                        score -= 2
                    if day_zhi_wx in jishen:
                        score -= 1

                    # 运势评分
                    for tg in [da_yun_ten_god, liu_nian_ten_god, liu_yue_ten_god]:
                        if tg in {"食神", "伤官", "正印", "七杀"}:
                            score += 1

                    return {
                        "日期": date_obj.isoformat(),
                        "日干支": f"{day_gan_curr}{day_zhi_curr}",
                        "吉神": sorted(list(ji_shen_set)),
                        "凶煞": sorted(list(xiong_sha_set)),
                        "五行(日干/支)": f"{day_gan_wx}/{day_zhi_wx}",
                        "得分": round(score, 2),
                        "吉神相关": task_yi_jishen.get(task, set()),
                        "煞神相关": task_ji_xiongsha.get(task, set()),
                    }
                except Exception as e:
                    return {
                        "日期": date_obj.isoformat(),
                        "日干支": "计算失败",
                        "吉神": [],
                        "凶煞": [],
                        "五行(日干/支)": "未知/未知",
                        "得分": 0,
                        "吉神相关": set(),
                        "煞神相关": set(),
                        "错误": str(e)
                    }

            # 扫描未来指定天数
            start_day = current_time.date()
            all_results = []
            
            result['prints'].append(f"\n📅 未来{days}天择吉推荐（任务：{task}）：")
            
            for i in range(days):
                d = start_day + timedelta(days=i)
                result1 = evaluate_day_for_task(
                    d,
                    task=task,
                    yongshen=yong_shen,
                    jishen=ji_shen,
                    day_gan=day_gan,
                    da_yun_ten_god=da_yun_ten_god,
                    liu_nian_ten_god=liu_nian_ten_god,
                    liu_yue_ten_god=liu_yue_ten_god
                )
                all_results.append(result1)

            # 在data中新增days结构
            result['data']['days'] = {
                'task': task,
                'recommend_days': [],
                'highest_scores': []
            }

            # 推荐日处理逻辑
            good_days = [r for r in all_results if r["得分"] >= 2]

            if not good_days:
                result['prints'].append(f"\n⚠️ 无得分 ≥ 2 的推荐日，推荐得分最高的前三日：")
                good_days = sorted(all_results, key=lambda x: x["得分"], reverse=True)[:3]
                result['data']['days']['recommend_type'] = 'highest_scores'
                result['data']['days']['highest_scores'] = [d['得分'] for d in good_days]
            else:
                result['prints'].append(f"\n📅 找到 {len(good_days)} 个推荐日：")
                result['data']['days']['recommend_type'] = 'qualified'

            # 结构化存储推荐日信息
            for idx, day in enumerate(good_days, 1):
                result['prints'].extend([
                    f"\n🎯 推荐日{idx}：{day['日期']} | 得分：{day['得分']}",
                    f"日干支：{day['日干支']}，五行：{day['五行(日干/支)']}",
                    f"吉神：{'、'.join(day['吉神']) if day['吉神'] else '无'}",
                    f"凶煞：{'、'.join(day['凶煞']) if day['凶煞'] else '无'}"
                ])

                # 结构化存储数据
                day_data = {
                    'ranking': idx,
                    'date': day['日期'],
                    'score': day['得分'],
                    'ganzhi': day['日干支'],
                    'wuxing': {
                        'gan': day['五行(日干/支)'].split('/')[0],
                        'zhi': day['五行(日干/支)'].split('/')[1]
                    },
                    'auspicious': day['吉神'],
                    'inauspicious': day['凶煞']
                }
                result['data']['days']['recommend_days'].append(day_data)

        return result

    except Exception as e:
        result['prints'].append(f"分析过程中出现错误: {str(e)}")
        result['prints'].append(f"错误详情: {traceback.format_exc()}")
        return result


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        print("收到参数：", data)
        
        params = {
            'birth_datetime': datetime.fromisoformat(data["birth_datetime"]),
            'gender': int(data["gender"]),
            'task': data["task"],
            'days': int(data["days"]),
            'current_time': datetime.fromisoformat(data["current_time"].replace("Z", ""))

        }

        analysis_result = run_bazi_analysis(**params)
        return jsonify({
            'status': 'success',
            'prints': analysis_result['prints'],
            'data': analysis_result['data']
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'参数解析失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 400


if __name__ == "__main__":
    app.run(debug=True)
