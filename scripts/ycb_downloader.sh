#!/bin/bash

# Declare an array of string with type
declare -a StringArray=("001_chips_can" "002_master_chef_can" "003_cracker_box" "004_sugar_box" "005_tomato_soup_can" "006_mustard_bottle" "007_tuna_fish_can" "008_pudding_box" "009_gelatin_box" "010_potted_meat_can" "011_banana" "012_strawberry" "013_apple" "014_lemon" "015_peach" "016_pear" "017_orange" "018_plum" "019_pitcher_base" "021_bleach_cleanser" "022_windex_bottle" "023_wine_glass" "024_bowl" "025_mug" "026_sponge" "027-skillet" "028_skillet_lid" "029_plate" "030_fork" "031_spoon" "032_knife" "033_spatula" "035_power_drill" "036_wood_block" "037_scissors" "038_padlock" "039_key" "040_large_marker" "041_small_marker" "042_adjustable_wrench" "043_phillips_screwdriver" "044_flat_screwdriver" "046_plastic_bolt" "047_plastic_nut" "048_hammer" "049_small_clamp" "050_medium_clamp" "051_large_clamp" "052_extra_large_clamp" "053_mini_soccer_ball" "054_softball" "055_baseball" "056_tennis_ball" "057_racquetball" "058_golf_ball" "059_chain" "061_foam_brick" "062_dice" "063-a_marbles" "063-b_marbles" "065-a_cups" "065-b_cups" "065-c_cups" "065-d_cups" "065-e_cups" "065-f_cups" "065-g_cups" "065-h_cups" "065-i_cups" "065-j_cups" "070-a_colored_wood_blocks" "070-b_colored_wood_blocks" "071_nine_hole_peg_test" "072-a_toy_airplane" "072-b_toy_airplane" "072-c_toy_airplane" "072-d_toy_airplane" "072-e_toy_airplane" "073-a_lego_duplo" "073-b_lego_duplo" "073-c_lego_duplo" "073-d_lego_duplo" "073-e_lego_duplo" "073-f_lego_duplo" "073-g_lego_duplo" "076_timer" "077_rubiks_cube")

for val in ${StringArray[@]}; do
   # wget "http://ycb-benchmarks.s3-website-us-east-1.amazonaws.com/data/berkeley/${val}/${val}_berkeley_rgbd.tgz" -P "/kuacc/users/bsefercik/dataset/ycb/"
   # tar -xvf "/kuacc/users/bsefercik/dataset/ycb/${val}_berkeley_rgbd.tgz" -C /kuacc/users/bsefercik/dataset/ycb/ &
   if [ -d "/kuacc/users/bsefercik/dataset/ycb/${val}" ]; then
      # if [ -d "/kuacc/users/bsefercik/dataset/ycb/${val}/clouds" ]; then
      #    if [ -z "$(ls -A /kuacc/users/bsefercik/dataset/ycb/${val}/clouds)" ]; then
      #       echo "Empty: ${val}"
      #    fi
      # else
      #    echo "Does not exist: ${val}"
      # fi
      echo "adsf"
   fi
done
wait
