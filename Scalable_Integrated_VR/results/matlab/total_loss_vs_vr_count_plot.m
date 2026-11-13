% Auto-generated MATLAB plot script
% Load data and reproduce the Total-Loss vs VR-Count figure.
% Edit freely – all source data is in the .mat file.

load('total_loss_vs_vr_count.mat');

figure('Name','Total Loss & Efficiency vs VR Count','NumberTitle','off');
yyaxis left
scatter_h = gobjects(numel(unique_topos), 1);
hold on;
plot(N_VRs, P_total_loss, '-', 'Color', [0.8 0.8 0.8], 'LineWidth', 1);
colors = lines(numel(unique_topos));
for i = 1:numel(unique_topos)
    mask = strcmp(topology, unique_topos{i});
    scatter_h(i) = scatter(N_VRs(mask), P_total_loss(mask), 50, colors(i,:), 'filled');
end
ylabel('Total Power Loss (W)');
xlabel('Number of VRs');

yyaxis right
plot(N_VRs, efficiency * 100, '--s', 'Color', [0.85 0.55 0], 'LineWidth', 2, ...
     'MarkerSize', 5, 'DisplayName', 'Efficiency');
ylabel('Efficiency (%)');

legend([scatter_h; plot(nan,nan,'--s','Color',[0.85 0.55 0])], ...
       [unique_topos; {'Efficiency'}], 'Location','best','FontSize',8);
title('Total Power Loss & Efficiency vs Number of VRs');
grid on;
