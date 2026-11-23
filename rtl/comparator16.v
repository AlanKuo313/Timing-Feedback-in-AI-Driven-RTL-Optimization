// Registered unsigned comparator. Outputs compare the inputs captured one edge earlier.
module comparator16 (
    input wire clk,
    input wire [15:0] a,
    input wire [15:0] b,
    output reg greater,
    output reg equal
);
    reg [15:0] a_reg, b_reg;
    always @(posedge clk) begin
        a_reg <= a;
        b_reg <= b;
        greater <= (a_reg > b_reg);
        equal <= (a_reg == b_reg);
    end
endmodule
