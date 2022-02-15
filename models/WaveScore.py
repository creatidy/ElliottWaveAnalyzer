from typing import List
from models.WaveAnalyzer import MonoWaveUp

class WaveScore:

    def __init__(self, waves: List[MonoWaveUp]):
        self.waves = waves
        self.no_of_waves = len(self.waves)


    def value(self):
        score = 0
        if self.no_of_waves == 5:
            wave1 = self.waves[0]
            wave2 = self.waves[1]
            wave3 = self.waves[2]
            wave4 = self.waves[3]
            wave5 = self.waves[4]

            score_wave2 = wave2.length / (0.618 * wave1.length)
            score_wave3 = wave3.length / (1.618 * wave1.length / wave3.length)
            score_wave4 = wave4.length / (0.382 * wave3.length)
            score_wave5 = wave5.length / wave1.length
            score_wave2 = 1 / score_wave2 if score_wave2 > 1 else score_wave2
            score_wave3 = 1 / score_wave3 if score_wave3 > 1 else score_wave3
            score_wave4 = 1 / score_wave4 if score_wave4 > 1 else score_wave4
            score_wave5 = 1 / score_wave5 if score_wave5 > 1 else score_wave5

            score = (score_wave2 + score_wave3 + score_wave4 + score_wave5) / 4

        return score
