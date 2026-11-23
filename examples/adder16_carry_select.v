// Example manually authored architectural candidate. 
// Its purpose is to smoke-test equivalence and the measurement pipeline.
module adder16 (
    input wire clk,
    input wire [15:0] a,
    input wire [15:0] b,
    output reg [16:0] sum
);
    reg [15:0] a_reg, b_reg;
    wire [8:0] low_sum = {1'b0, a_reg[7:0]} + {1'b0, b_reg[7:0]};
    wire [8:0] upper_sum0 = {1'b0, a_reg[15:8]} + {1'b0, b_reg[15:8]};
    wire [8:0] upper_sum1 = {1'b0, a_reg[15:8]} + {1'b0, b_reg[15:8]} + 9'd1;
    wire [8:0] chosen_upper = low_sum[8] ? upper_sum1 : upper_sum0;
    always @(posedge clk) begin
        a_reg <= a;
        b_reg <= b;
        sum <= {chosen_upper, low_sum[7:0]};
    end
endmodule
