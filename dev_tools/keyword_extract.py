import itertools
import os
import re
from collections import defaultdict
from functools import cache
from hashlib import md5

from dev_tools.keywords.base import TextMap, UI_LANGUAGES, replace_templates, text_to_variable
from module.base.code_generator import CodeGenerator
from module.config.deep import deep_get
from module.config.utils import read_file
from module.logger import logger


def blessing_name(name: str) -> str:
    name = text_to_variable(name)
    name = re.sub(r'^\d', lambda match: f"_{match.group(0)}", name)
    return name


class KeywordExtract:
    def __init__(self):
        self.text_map: dict[str, TextMap] = {lang: TextMap(lang) for lang in UI_LANGUAGES}
        # self.text_map['cn'] = TextMap('chs')
        self.keywords_id: list[int] = []

    def find_keyword(self, keyword, lang) -> tuple[int, str]:
        """
        Args:
            keyword: text string or text id
            lang: Language to find

        Returns:
            text id (hash in TextMap)
            text
        """
        text_map = self.text_map[lang]
        return text_map.find(keyword)

    def load_keywords(self, keywords: list[str | int], lang='cn'):
        text_map = self.text_map[lang]
        keywords_id = [text_map.find(keyword) for keyword in keywords]
        self.keywords_id = [keyword[0] for keyword in keywords_id if keyword[0] != 0 and keyword[1].strip()]

    def clear_keywords(self):
        self.keywords_id = []

    def write_keywords(
            self,
            keyword_class,
            output_file: str = '',
            text_convert=text_to_variable,
            generator: CodeGenerator = None,
            extra_attrs: dict[str, dict] = None
    ):
        """
        Args:
            keyword_class:
            output_file:
            text_convert:
            generator: Reuse an existing code generator
            extra_attrs: Extra attributes write in keywords
        """
        if generator is None:
            gen = CodeGenerator()
            gen.Import(f"""
            from .classes import {keyword_class}
            """)
            gen.CommentAutoGenerage('dev_tools.keyword_extract')
        else:
            gen = generator

        last_id = getattr(gen, 'last_id', 0)
        if extra_attrs:
            keyword_num = len(self.keywords_id)
            for attr_key, attr_value in extra_attrs.items():
                if len(attr_value) != keyword_num:
                    print(f"Extra attribute {attr_key} does not match the size of keywords")
                    return
        for index, keyword in enumerate(self.keywords_id):
            _, name = self.find_keyword(keyword, lang='en')
            name = text_convert(replace_templates(name))
            with gen.Object(key=name, object_class=keyword_class):
                gen.ObjectAttr(key='id', value=index + last_id + 1)
                gen.ObjectAttr(key='name', value=name)
                for lang in UI_LANGUAGES:
                    gen.ObjectAttr(key=lang, value=replace_templates(self.find_keyword(keyword, lang=lang)[1]))
                if extra_attrs:
                    for attr_key, attr_value in extra_attrs.items():
                        gen.ObjectAttr(key=attr_key, value=attr_value[keyword])
                gen.last_id = index + last_id + 1

        if output_file:
            print(f'Write {output_file}')
            gen.write(output_file)
            self.clear_keywords()
        return gen

    def load_quests(self, quests, lang='cn'):
        """
        Load a set of quest keywords

        Args:
            quests: iterable quest id collection
            lang:

        """
        quest_data = read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'QuestData.json'))
        quest_data = {
            str(deep_get(data, 'QuestID')): data
            for data in quest_data
        }
        quests_hash = [quest_data[str(quest_id)]["QuestTitle"]["Hash"] for quest_id in quests]
        quest_keywords = list(dict.fromkeys([self.text_map[lang].find(quest_hash)[1] for quest_hash in quests_hash]))
        self.load_keywords(quest_keywords, lang)

    def write_daily_quest_keywords(self):
        text_convert = text_to_variable
        keyword_class = 'DailyQuest'
        gen = CodeGenerator()
        gen.Import(f"""
        from .classes import {keyword_class}
        """)
        gen.CommentAutoGenerage('dev_tools.keyword_extract')

        old_quest = [
            "Go_on_assignment_1_time",  # -> Dispatch_1_assignments
            "Complete_Simulated_Universe_1_times",  # same
            "Complete_1_stage_in_Simulated_Universe_Any_world",
            # -> Complete_Divergent_Universe_or_Simulated_Universe_1_times
            "Complete_Calyx_Crimson_1_time",  # -> Clear_Calyx_Crimson_1_times
            "Enter_combat_by_attacking_enemy_Weakness_and_win_3_times",
            # -> Enter_combat_by_attacking_enemie_Weakness_and_win_1_times
            "Use_Technique_2_times",  # -> Use_Technique_1_times
            "Destroy_3_destructible_objects",  # -> Destroy_1_destructible_objects
            "Obtain_victory_in_combat_with_Support_Characters_1_time",
            # -> Obtain_victory_in_combat_with_Support_Characters_1_times
            "Level_up_any_character_1_time",  # -> Level_up_any_character_1_times
            "Level_up_any_Light_Cone_1_time",  # -> Level_up_any_Light_Cone_1_times
            "Synthesize_Consumable_1_time",  # -> Use_the_Omni_Synthesizer_1_times
            "Synthesize_material_1_time",  # -> Use_the_Omni_Synthesizer_1_times
            "Take_1_photo",  # -> Take_photos_1_times
            "Level_up_any_Relic_1_time",  # -> Level_up_any_Relic_1_times
        ]

        correct_times = {
            #    "Dispatch_1_assignments":  1,
            #    "Complete_Divergent_Universe_or_Simulated_Universe_1_times": 1,
            #    "Clear_Calyx_Crimson_1_times": 1,
            "Enter_combat_by_attacking_enemie_Weakness_and_win_1_times": 3,
            "Use_Technique_1_times": 2,
            "Destroy_1_destructible_objects": 3,
            #    "Obtain_victory_in_combat_with_Support_Characters_1_times": 1,
            #    "Level_up_any_character_1_times": 1,
            #    "Level_up_any_Light_Cone_1_times": 1,
            #    "Use_the_Omni_Synthesizer_1_times": 1,
            #    "Take_photos_1_times": 1,
            #    "Level_up_any_Relic_1_times": 1,
            "Consume_1_Trailblaze_Power": 120

        }

        def replace_templates_quest(text: str, correct_time=1) -> str:
            text = replace_templates(text)
            text = text.replace('1', f'{correct_time}')
            return text

        last_id = getattr(gen, 'last_id', 0)
        for index, keyword in enumerate(self.keywords_id):
            _, old_name = self.find_keyword(keyword, lang='en')
            old_name = text_convert(replace_templates(old_name))
            if old_name in old_quest:
                continue
            name = old_name.replace('1', str(correct_times.setdefault(old_name, 1)))

            with gen.Object(key=name, object_class=keyword_class):
                gen.ObjectAttr(key='id', value=index + last_id + 1)
                gen.ObjectAttr(key='name', value=name)
                for lang in UI_LANGUAGES:
                    gen.ObjectAttr(key=lang, value=replace_templates_quest(self.find_keyword(keyword, lang=lang)[1],
                                                                           correct_times.setdefault(old_name, 1)))
                gen.last_id = index + last_id + 1

        output_file = './tasks/daily/keywords/daily_quest.py'
        print(f'Write {output_file}')
        gen.write(output_file)
        self.clear_keywords()
        return gen

    def generate_daily_quests(self):
        daily_quest = read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'DailyQuest.json'))
        self.load_quests([str(deep_get(data, 'DailyID')) for data in daily_quest])
        self.write_daily_quest_keywords()

    def generate_shadow_with_characters(self):
        # Damage type -> damage hash
        damage_info = dict()
        for data in read_file(os.path.join(
                TextMap.DATA_FOLDER, 'ExcelOutput',
                'DamageType.json'
        )):
            type_name = deep_get(data, 'ID', 0)
            damage_info[type_name] = deep_get(data, 'DamageTypeName.Hash')
        # Character id -> character hash & damage type
        character_info = dict()
        for data in read_file(os.path.join(
                TextMap.DATA_FOLDER, 'ExcelOutput',
                'AvatarConfig.json'
        )):
            voice = deep_get(data, 'AvatarVOTag', default='')
            if voice == 'test':
                continue
            name_hash = deep_get(data, 'AvatarName.Hash')
            damage_type = deep_get(data, 'DamageType')
            character_info[data['AvatarID']] = (
                name_hash, damage_info[damage_type])
        # Item id -> character id
        promotion_info = defaultdict(list)

        def merge_same(data: list[dict], keyword) -> list:
            mp = defaultdict(dict)
            for d in data:
                length = len(mp[d[keyword]])
                mp[d[keyword]][str(length)] = d
            return mp.values()

        for data in merge_same(read_file(os.path.join(
                TextMap.DATA_FOLDER, 'ExcelOutput',
                'AvatarPromotionConfig.json'
        )), keyword='AvatarID'):
            character_id = deep_get(data, '0.AvatarID')
            item_id = deep_get(data, '2.PromotionCostList')[-1]['ItemID']
            try:
                promotion_info[item_id].append(character_info[character_id])
            except KeyError:
                pass
        # Shadow hash -> item id
        shadow_info = dict()
        for data in merge_same(read_file(os.path.join(
                TextMap.DATA_FOLDER, 'ExcelOutput',
                'MappingInfo.json'
        )), keyword='ID'):
            farm_type = deep_get(data, '0.FarmType')
            if farm_type != 'ELEMENT':
                continue
            shadow_hash = deep_get(data, '0.Name.Hash')
            item_id = deep_get(data, '5.DisplayItemList')[-1]['ItemID']
            shadow_info[shadow_hash] = promotion_info[item_id]
        prefix_dict = {
            'cn': '晋阶材料：',
            'cht': '晉階材料：',
            'jp': '昇格素材：',
            'en': 'Ascension: ',
            'es': 'Ascension: '
        }
        keyword_class = 'DungeonDetailed'
        output_file = './tasks/dungeon/keywords/dungeon_detailed.py'
        gen = CodeGenerator()
        gen.Import(f"""
        from .classes import {keyword_class}
        """)
        gen.CommentAutoGenerage('dev_tools.keyword_extract')
        for index, (keyword, characters) in enumerate(shadow_info.items()):
            if not characters:
                continue
            _, name = self.find_keyword(keyword, lang='en')
            name = text_to_variable(name).replace('Shape_of_', '')
            with gen.Object(key=name, object_class=keyword_class):
                gen.ObjectAttr(key='id', value=index + 1)
                gen.ObjectAttr(key='name', value=name)
                for lang in UI_LANGUAGES:
                    character_names = [
                        replace_templates(self.find_keyword(c[0], lang)[1])
                        for c in characters
                    ]
                    character_names = list(dict.fromkeys(character_names))
                    character_names = ' / '.join(character_names)
                    damage_type = self.find_keyword(characters[0][1], lang)[1]
                    if lang in {'en', 'es'}:
                        value = f'{prefix_dict[lang]}{damage_type} ({character_names})'
                    else:
                        value = f'{prefix_dict[lang]}{damage_type}（{character_names}）'
                    gen.ObjectAttr(key=lang, value=value)
        print(f'Write {output_file}')
        gen.write(output_file)
        self.clear_keywords()

    def generate_forgotten_hall_stages(self):
        keyword_class = "ForgottenHallStage"
        output_file = './tasks/forgotten_hall/keywords/stage.py'
        gen = CodeGenerator()
        gen.Import(f"""
        from .classes import {keyword_class}
        """)
        gen.CommentAutoGenerage('dev_tools.keyword_extract')
        for stage_id in range(1, 16):
            id_str = str(stage_id).rjust(2, '0')
            with gen.Object(key=f"Stage_{stage_id}", object_class=keyword_class):
                gen.ObjectAttr(key='id', value=stage_id)
                gen.ObjectAttr(key='name', value=id_str)
                for lang in UI_LANGUAGES:
                    gen.ObjectAttr(key=lang, value=id_str)

        print(f'Write {output_file}')
        gen.write(output_file)
        self.clear_keywords()

    def generate_assignments(self):
        from dev_tools.keywords.assignment import GenerateAssignment
        GenerateAssignment()()

    def generate_map_planes(self):
        from dev_tools.keywords.map_world import GenerateMapWorld
        GenerateMapWorld()()
        from dev_tools.keywords.map_plane import GenerateMapPlane
        GenerateMapPlane()()

    def generate_character_keywords(self):
        from dev_tools.keywords.character import GenerateCharacterList, GenerateCharacterHeight, GenerateCombatType
        GenerateCharacterList()()
        GenerateCharacterHeight()()
        GenerateCombatType()()

    def generate_battle_pass_quests(self):
        battle_pass_quests = read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'BattlePassConfig.json'))
        latest_quests = list(battle_pass_quests)[-1]
        week_quest_list = deep_get(latest_quests, "WeekQuestList")
        week_order1 = deep_get(latest_quests, "WeekOrder1")
        week_chain_quest_list = deep_get(latest_quests, "WeekChainQuestList")
        quests = week_quest_list + week_order1 + week_chain_quest_list
        self.load_quests(quests)
        self.write_keywords(keyword_class='BattlePassQuest', output_file='./tasks/battle_pass/keywords/quest.py')

    def generate_rogue_buff(self):
        # paths
        aeons = read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'RogueAeonDisplay.json'))
        aeons_hash = [deep_get(aeon, 'RogueAeonPathName2.Hash') for aeon in aeons]
        self.keywords_id = aeons_hash
        self.write_keywords(keyword_class='RoguePath', output_file='./tasks/rogue/keywords/path.py')

        # blessings
        blessings_info = read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'RogueBuff.json'))
        blessings_name_map = read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'RogueMazeBuff.json'))
        blessings_name_map = {
            deep_get(data, 'ID'): data
            for data in blessings_name_map
        }
        blessings_id = [deep_get(blessing, 'MazeBuffID') for blessing in blessings_info
                        if not deep_get(blessing, 'AeonID')][1:]
        resonances_id = [deep_get(blessing, 'MazeBuffID') for blessing in blessings_info
                         if deep_get(blessing, 'AeonID')]
        blessings_info = {
            str(deep_get(data, 'MazeBuffID')): data
            for data in blessings_info if deep_get(data, 'MazeBuffLevel') == 1
        }

        # ignore endless buffs
        endless_buffs = read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'RogueEndlessMegaBuffDesc.json'))
        endless_buff_ids = [int(deep_get(data, 'MazeBuffID')) for data in endless_buffs]
        blessings_id = [id_ for id_ in blessings_id if id_ not in endless_buff_ids]

        def get_blessing_infos(id_list, with_enhancement: bool):
            blessings_hash = [deep_get(blessings_name_map, f"{blessing_id}.BuffName.Hash")
                              for blessing_id in id_list]
            blessings_path_id = {blessing_hash: int(deep_get(blessings_info, f'{blessing_id}.RogueBuffType')) - 119
                                 # 119 is the magic number make type match with path in keyword above
                                 for blessing_hash, blessing_id in zip(blessings_hash, id_list)}
            blessings_category = {blessing_hash: deep_get(blessings_info, f'{blessing_id}.RogueBuffCategory')
                                  for blessing_hash, blessing_id in zip(blessings_hash, id_list)}
            category_map = {
                "Common": 1,
                "Rare": 2,
                "Legendary": 3,
            }
            blessings_rarity = {blessing_hash: category_map[blessing_category]
                                for blessing_hash, blessing_category in blessings_category.items()}
            enhancement = {blessing_hash: "" for blessing_hash in blessings_hash}
            if with_enhancement:
                return blessings_hash, {'path_id': blessings_path_id, 'rarity': blessings_rarity,
                                        'enhancement': enhancement}
            else:
                return blessings_hash, {'path_id': blessings_path_id, 'rarity': blessings_rarity}

        hash_list, extra_attrs = get_blessing_infos(blessings_id, with_enhancement=True)
        self.keywords_id = hash_list
        self.write_keywords(keyword_class='RogueBlessing', output_file='./tasks/rogue/keywords/blessing.py',
                            text_convert=blessing_name, extra_attrs=extra_attrs)

        hash_list, extra_attrs = get_blessing_infos(resonances_id, with_enhancement=False)
        self.keywords_id = hash_list
        self.write_keywords(keyword_class='RogueResonance', output_file='./tasks/rogue/keywords/resonance.py',
                            text_convert=blessing_name, extra_attrs=extra_attrs)

    def generate_rogue_events(self):
        # An event contains several options
        event_title_file = os.path.join(
            TextMap.DATA_FOLDER, 'ExcelOutput',
            'RogueTalkNameConfig.json'
        )
        event_title_ids = {
            str(deep_get(data, 'TalkNameID')): deep_get(data, 'Name.Hash')
            for data in read_file(event_title_file)
        }
        event_title_texts = defaultdict(list)
        for title_id, title_hash in event_title_ids.items():
            if title_hash not in self.text_map['en']:
                continue
            _, title_text = self.find_keyword(title_hash, lang='en')
            event_title_texts[text_to_variable(title_text)].append(title_id)
        option_file = os.path.join(
            TextMap.DATA_FOLDER, 'ExcelOutput',
            'RogueDialogueOptionDisplay.json'
        )
        option_ids = {
            str(deep_get(data, 'OptionDisplayID')): deep_get(data, 'OptionTitle.Hash')
            for data in read_file(option_file)
        }
        # Key: event name hash, value: list of option id/hash
        options_grouped = dict()
        # Key: option md5, value: option text hash in StarRailData
        option_md5s = dict()

        @cache
        def get_option_md5(option_hash):
            m = md5()
            for lang in UI_LANGUAGES:
                option_text = self.find_keyword(option_hash, lang=lang)[1]
                m.update(option_text.encode())
            return m.hexdigest()

        # Drop invalid or duplicate options
        def clean_options(options):
            visited = set()
            for i in options:
                option_hash = option_ids[str(i)]
                if option_hash not in self.text_map['en']:
                    continue
                option_md5 = get_option_md5(option_hash)
                if option_md5 in visited:
                    continue
                if option_md5 not in option_md5s:
                    option_md5s[option_md5] = option_hash
                visited.add(option_md5)
                yield option_md5s[option_md5]

        for group_title_ids in event_title_texts.values():
            group_option_ids = []
            for title_id in group_title_ids:
                # Special case for Nildis (尼尔迪斯牌)
                # Missing option: Give up
                if title_id == '13501':
                    group_option_ids.append(13506)
                option_id = title_id
                # title ids in Swarm Disaster (寰宇蝗灾) have a "1" prefix
                if option_id not in option_ids:
                    option_id = title_id[1:]
                # Some title may not has corresponding options
                if option_id not in option_ids:
                    continue
                group_option_ids += list(itertools.takewhile(
                    lambda x: str(x) in option_ids,
                    itertools.count(int(option_id))
                ))
            if group_option_ids:
                title_hash = event_title_ids[group_title_ids[0]]
                options_grouped[title_hash] = group_option_ids

        for title_hash, options in options_grouped.items():
            options_grouped[title_hash] = list(clean_options(options))
        for title_hash in list(options_grouped.keys()):
            if len(options_grouped[title_hash]) == 0:
                options_grouped.pop(title_hash)
        option_dup_count = defaultdict(int)
        for option_hash in option_md5s.values():
            if option_hash not in self.text_map['en']:
                continue
            _, option_text = self.find_keyword(option_hash, lang='en')
            option_dup_count[text_to_variable(option_text)] += 1

        def option_text_convert(option_md5, md5_prefix_len=4):
            def wrapper(option_text):
                option_var = text_to_variable(option_text)
                if option_dup_count[option_var] > 1:
                    option_var = f'{option_var}_{option_md5[:md5_prefix_len]}'
                return option_var

            return wrapper

        option_gen = None
        option_hash_to_keyword_id = dict()  # option hash -> option keyword id
        for i, (option_md5, option_hash) in enumerate(option_md5s.items(), start=1):
            self.load_keywords([option_hash])
            option_gen = self.write_keywords(
                keyword_class='RogueEventOption',
                text_convert=option_text_convert(option_md5),
                generator=option_gen
            )
            option_hash_to_keyword_id[option_hash] = i
        output_file = './tasks/rogue/keywords/event_option.py'
        print(f'Write {output_file}')
        option_gen.write(output_file)

        # title hash -> option keyword id
        title_to_option_keyword_id = {
            title_hash: sorted(
                option_hash_to_keyword_id[x] for x in option_hashes
            ) for title_hash, option_hashes in options_grouped.items()
        }
        self.load_keywords(options_grouped.keys())
        self.write_keywords(
            keyword_class='RogueEventTitle',
            output_file='./tasks/rogue/keywords/event_title.py',
            extra_attrs={'option_ids': title_to_option_keyword_id}
        )
        try:
            from tasks.rogue.event.event import OcrRogueEventOption
        except AttributeError as e:
            logger.error(e)
            logger.critical(
                f'Importing OcrRogueEventOption fails, probably due to changes in {output_file}')
        try:
            from tasks.rogue.event.preset import STRATEGIES
        except AttributeError as e:
            logger.error(e)
            logger.critical(
                f'Importing preset strategies fails, probably due to changes in {output_file}')

    def iter_without_duplication(self, file: list, keys):
        visited = set()
        for data in file:
            hash_ = deep_get(data, keys=keys)
            _, name = self.find_keyword(hash_, lang='cn')
            if name in visited:
                continue
            visited.add(name)
            yield hash_

    def generate(self):
        self.load_keywords(['饰品提取', '差分宇宙', '模拟宇宙',
                            '拟造花萼（金）', '拟造花萼（赤）', '凝滞虚影', '侵蚀隧洞', '历战余响',
                            '最近更新', '忘却之庭', '虚构叙事', '末日幻影'])
        self.write_keywords(keyword_class='DungeonNav', output_file='./tasks/dungeon/keywords/nav.py')
        self.load_keywords(['行动摘要', '生存索引', '每日实训', '模拟宇宙', '逐光捡金', '战术训练'])
        self.write_keywords(keyword_class='DungeonTab', output_file='./tasks/dungeon/keywords/tab.py')
        self.load_keywords(['前往', '领取', '进行中', '已领取', '本日活跃度已满'])
        self.write_keywords(keyword_class='DailyQuestState', output_file='./tasks/daily/keywords/daily_quest_state.py')
        self.load_keywords(['领取', '追踪'])
        self.write_keywords(keyword_class='BattlePassQuestState',
                            output_file='./tasks/battle_pass/keywords/quest_state.py')
        self.generate_map_planes()
        self.generate_character_keywords()
        from dev_tools.keywords.cone import generate_cone
        generate_cone()
        from dev_tools.keywords.dungeon_list import GenerateDungeonList
        GenerateDungeonList()()
        self.load_keywords(['进入', '传送', '追踪'])
        self.write_keywords(keyword_class='DungeonEntrance', output_file='./tasks/dungeon/keywords/dungeon_entrance.py')
        self.generate_shadow_with_characters()
        self.load_keywords(['奖励', '任务', ])
        self.write_keywords(keyword_class='BattlePassTab', output_file='./tasks/battle_pass/keywords/tab.py')
        self.load_keywords(['本周任务', '本期任务'])
        self.write_keywords(keyword_class='BattlePassMissionTab',
                            output_file='./tasks/battle_pass/keywords/mission_tab.py')
        self.generate_assignments()
        self.generate_forgotten_hall_stages()
        self.generate_daily_quests()
        self.generate_battle_pass_quests()
        self.load_keywords(['养成材料', '光锥', '遗器', '其他材料', '消耗品', '任务', '贵重物', '材料置换', '随宠'])
        self.write_keywords(keyword_class='ItemTab',
                            text_convert=lambda name: name.replace(' ', '').replace('LightCones', 'LightCone'),
                            output_file='./tasks/item/keywords/tab.py')
        from dev_tools.keywords.item import generate_items
        generate_items()
        from dev_tools.keywords.relics import generate_relics
        generate_relics()
        self.generate_rogue_buff()
        self.load_keywords(['已强化'])
        self.write_keywords(keyword_class='RogueEnhancement', output_file='./tasks/rogue/keywords/enhancement.py')
        self.load_keywords(list(self.iter_without_duplication(
            read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'RogueMiracleDisplay.json')),
            'MiracleName.Hash')))
        self.write_keywords(keyword_class='RogueCurio', output_file='./tasks/rogue/keywords/curio.py')
        self.load_keywords(list(self.iter_without_duplication(
            read_file(os.path.join(TextMap.DATA_FOLDER, 'ExcelOutput', 'RogueBonus.json')), 'BonusTitle.Hash')))
        self.write_keywords(keyword_class='RogueBonus', output_file='./tasks/rogue/keywords/bonus.py')
        self.generate_rogue_events()


if __name__ == '__main__':
    TextMap.DATA_FOLDER = '../turnbasedgamedata'
    KeywordExtract().generate()
